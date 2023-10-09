import uuid
from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.models.envelope import EnvelopeSearchItem
from app.esign.models.envelope_callback import EnvelopeCallbackSearchItem
from app.esign.repositories.envelope import EnvelopeRepository
from app.esign.repositories.envelope_callback import EnvelopeCallbackRepository
from app.esign.schema.envelope import DSEnvelopeRequest
from app.file_storage.service import FileStorageService
from tests.constants import DATA_CONTAINER_PATH, SIGNED_DOCUMENT_PDF
from tests.esign.builders import (
    EnvelopeCreateResponseTuple,
    build_envelope_documents_response,
    build_webhook_event,
)

ESIGN_WEBHOOK_ADDRESS = "/api/v1/esign/webhook"


@pytest.mark.asyncio
async def test_returns422_on_incorrect_status_event_name(
    client: AsyncClient,
):
    request = build_webhook_event(status="not-correct-event")
    response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=request)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {
        "detail": [
            {
                "field": "status",
                "message":
                    "value is not a valid enumeration member; permitted: "
                    + "'authoritativecopy', 'completed', 'correct', "
                    + "'created', 'declined', 'deleted', 'delivered', "
                    + "'sent', 'signed', 'template', 'timedout', "
                    + "'transfercompleted', 'voided', 'custom:creating'",
                "type": "type_error.enum"
            }
        ]
    }


@pytest.mark.asyncio
async def test_should_return200_and_save_event_in_dynamodb(
    client: AsyncClient,
    app_container: Container,
    envelope_repository: EnvelopeRepository,
    mock_store_signed_documents_in_bucket: None,
):
    request = build_webhook_event()
    envelope_id = request["envelopeId"]
    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=request)

    envelope = await envelope_repository.get_item(EnvelopeSearchItem(envelope_id=envelope_id))

    assert response.status_code == status.HTTP_200_OK
    assert envelope is not None
    assert envelope.envelope_id == envelope_id


@pytest.mark.asyncio
async def test_should_return200_and_update_event(
    client: AsyncClient,
    envelope_repository: EnvelopeRepository,
    app_container: Container,
    mock_store_signed_documents_in_bucket: None,
):
    first_request = build_webhook_event(changed_date_time=datetime.utcnow())
    envelope_id = first_request["envelopeId"]
    second_request = build_webhook_event(status=EnvelopeStatusEnum.voided, envelope_id=envelope_id)

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        first_response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=first_request)
        second_response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=second_request)

    envelope = await envelope_repository.get_item(EnvelopeSearchItem(envelope_id=envelope_id))

    assert envelope is not None
    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK
    assert envelope.envelope_status == EnvelopeStatusEnum.voided.value


@pytest.mark.asyncio
async def test_should_return200_and_save_file_without_certificate_when_status_is_completed(
    client: AsyncClient,
    main_bucket_name: str,
    storage_service: FileStorageService,
    app_container: Container,
):
    request = build_webhook_event(
        changed_date_time=datetime.utcnow(),
        status=EnvelopeStatusEnum.completed
    )
    envelope_id = request["envelopeId"]
    envelope_documents_response = build_envelope_documents_response(envelope_id)
    document_id = envelope_documents_response.envelope_documents[0].document_id_guid
    certificate_id = envelope_documents_response.envelope_documents[1].document_id_guid

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.list_documents.return_value = envelope_documents_response

    with open(DATA_CONTAINER_PATH / SIGNED_DOCUMENT_PDF, mode="rb") as signed_document_file:
        docusign_client_mock.get_document_by_id.return_value = BytesIO(signed_document_file.read())

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=request)

    document_path = f"signed-documents/{envelope_id}/{document_id}.pdf"
    is_document_exist = await storage_service.is_object_exists(main_bucket_name, document_path)

    certificate_path = f"signed-documents/{envelope_id}/{certificate_id}.pdf"
    is_certificate_exist = await storage_service.is_object_exists(main_bucket_name, certificate_path)

    assert is_document_exist
    assert not is_certificate_exist
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_should_return200_process_webhook_and_send_notification_application(
    client: AsyncClient,
    valid_envelope_schema: DSEnvelopeRequest,
    mocker: MockerFixture,
    app_container: Container,
    mock_store_signed_documents_in_bucket: None,
):
    mocked_async_client = mocker.patch("app.esign.services.webhook.AsyncClient")
    mocked_client = AsyncMock()
    mocked_client.post.return_value = Response(status_code=status.HTTP_200_OK, request=Mock())
    mocked_async_client.return_value.__aenter__.return_value = mocked_client  # noqa: WPS609

    callback_url = "https://www.lipsum.com/"
    request_data = valid_envelope_schema.dict() | {"callbackUrl": callback_url}

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.create_envelope.return_value = EnvelopeCreateResponseTuple(envelope_id=str(uuid.uuid4()))

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        create_response = await client.post("/api/v1/esign/envelope", json=request_data)
        envelope_id = create_response.json()["envelopeId"]

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)
    data_request = build_webhook_event(changed_date_time=datetime.utcnow(), envelope_id=envelope_id)

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        process_webhook_response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=data_request)

    data_called = mocked_client.mock_calls[0].kwargs

    assert (
        create_response.status_code == status.HTTP_200_OK
        and process_webhook_response.status_code == status.HTTP_200_OK
    )
    assert process_webhook_response.status_code == status.HTTP_200_OK
    assert data_called["url"] == callback_url

    assert (
        data_called["json"]["envelopeId"] == envelope_id
        and data_called["json"]["envelopeStatus"] == EnvelopeStatusEnum.sent.value
    )


@pytest.mark.asyncio
async def test_should_return200_process_webhook_with_voided_status(
    client: AsyncClient,
    valid_envelope_schema: DSEnvelopeRequest,
    mocker: MockerFixture,
    app_container: Container,
    envelope_repository: EnvelopeRepository,
    envelope_callback_repository: EnvelopeCallbackRepository,
    mock_store_signed_documents_in_bucket: None,
):
    mocked_async_client = mocker.patch("app.esign.services.webhook.AsyncClient")
    mocked_client = AsyncMock()
    mocked_client.post.return_value = Response(status_code=status.HTTP_200_OK, request=Mock())
    mocked_async_client.return_value.__aenter__.return_value = mocked_client  # noqa: WPS609

    callback_url = "https://www.lipsum.com/"
    request_data = valid_envelope_schema.dict() | {"callbackUrl": callback_url}

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.create_envelope.return_value = EnvelopeCreateResponseTuple(envelope_id=str(uuid.uuid4()))

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        create_response = await client.post("/api/v1/esign/envelope", json=request_data)
        envelope_id = create_response.json()["envelopeId"]

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)
    webhook_first_request = build_webhook_event(changed_date_time=datetime.utcnow(), envelope_id=envelope_id)
    webhook_second_request = build_webhook_event(
        status=EnvelopeStatusEnum.voided,
        changed_date_time=datetime.utcnow(),
        envelope_id=envelope_id
    )

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        webhook_first_response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=webhook_first_request)
        webhook_second_response = await client.post(ESIGN_WEBHOOK_ADDRESS, json=webhook_second_request)

    envelope = await envelope_repository.get_item(EnvelopeSearchItem(envelope_id=envelope_id))
    envelope_callback = await envelope_callback_repository.get_item(
        EnvelopeCallbackSearchItem(envelope_id=envelope_id)
    )
    data_called = mocked_client.mock_calls[1].kwargs

    assert (
        webhook_first_response.status_code == status.HTTP_200_OK
        and webhook_second_response.status_code == status.HTTP_200_OK
    )
    assert (
        data_called["json"]["envelopeId"] == envelope_id
        and data_called["url"] == callback_url
        and data_called["json"]["envelopeStatus"] == EnvelopeStatusEnum.voided.value
    )
    assert envelope and envelope_callback
    assert (
        envelope.expiration_time
        and envelope_callback.expiration_time
        and envelope.expiration_time == envelope_callback.expiration_time
    )
