import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import status
from httpx import AsyncClient, Response
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.schema.envelope import DSEnvelopeRequest
from tests.esign.builders import (
    EnvelopeCreateResponseTuple,
    build_envelope_documents_response,
    build_envelope_recipients_response,
)


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.patch("/api/v1/esign/envelope/123/webhook/redeliver", headers={"Authorization": "rand"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return200_redeliver_webhook_and_put_callback_url(
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
    create_request_data = valid_envelope_schema.dict()
    redeliver_webhook_request = {"callbackUrl": callback_url}

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.create_envelope.return_value = EnvelopeCreateResponseTuple(envelope_id=str(uuid.uuid4()))

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        create_response = await client.post("/api/v1/esign/envelope", json=create_request_data)
        envelope_id = create_response.json()["envelopeId"]

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.get_envelope.return_value = build_envelope_recipients_response(envelope_id)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        process_webhook_response = await client.patch(
            f"/api/v1/esign/envelope/{envelope_id}/webhook/redeliver",
            json=redeliver_webhook_request
        )

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
async def test_should_return200_redeliver_webhook_and_update_callback_url(
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

    first_callback_url = "https://httpbin.org/post"
    second_callback_url = "https://www.lipsum.com/"
    create_request_data = valid_envelope_schema.dict() | {"callbackUrl": first_callback_url}

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.create_envelope.return_value = EnvelopeCreateResponseTuple(envelope_id=str(uuid.uuid4()))

    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        create_response = await client.post("/api/v1/esign/envelope", json=create_request_data)
        envelope_id = create_response.json()["envelopeId"]

    docusign_client_mock = AsyncMock(spec=DocuSignClient)
    docusign_client_mock.get_envelope.return_value = build_envelope_recipients_response(envelope_id)
    docusign_client_mock.list_documents.return_value = build_envelope_documents_response(envelope_id)

    redeliver_webhook_request = {"callbackUrl": second_callback_url}
    app_container.esign_webhook_service.reset()
    with app_container.docusign_client.override(docusign_client_mock):
        process_webhook_response = await client.patch(
            f"/api/v1/esign/envelope/{envelope_id}/webhook/redeliver",
            json=redeliver_webhook_request
        )

    data_called = mocked_client.mock_calls[0].kwargs

    assert (
        create_response.status_code == status.HTTP_200_OK
        and process_webhook_response.status_code == status.HTTP_200_OK
    )
    assert process_webhook_response.status_code == status.HTTP_200_OK
    assert data_called["url"] == second_callback_url

    assert (
        data_called["json"]["envelopeId"] == envelope_id
        and data_called["json"]["envelopeStatus"] == EnvelopeStatusEnum.sent.value
    )
