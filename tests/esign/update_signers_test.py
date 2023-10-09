import json
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
from docusign_esign import (
    ApiException,
    ErrorDetails,
    Recipients,
    RecipientsUpdateSummary,
    RecipientUpdateResponse,
    Signer,
)
from fastapi import status
from httpx import AsyncClient
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import ExcErrorCodeEnum
from app.esign.models.envelope import EnvelopePutItem

SIGNER1_GUID = "3970c7c4-41e8-4dce-82c3-0c50470f2516"
SIGNER1_EMAIL = "signer1@email.example"
SIGNER1_NAME = "Signer 1 Name"

SIGNER2_GUID = "64cd3b06-a7d2-4523-b417-a56c590c54db"
SIGNER2_EMAIL = "signer2@email.example"
SIGNER2_NAME = "Signer 2 Name"

ERROR_DETAILS = "Recipients update failed"


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.put(
        "/api/v1/esign/envelope/123/signers",
        json={},
        headers={"Authorization": "rand"},
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return200_on_updated_signers(
    client: AsyncClient,
    app_container: Container,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    recipient_update_summary = RecipientsUpdateSummary(
        recipient_update_results=[
            RecipientUpdateResponse(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                error_details=None,
            ),
        ],
    )
    recipients = Recipients(
        signers=[
            Signer(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                email=SIGNER1_EMAIL,
                name=SIGNER1_NAME,
            ),
        ],
    )
    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.update_recipients.return_value = recipient_update_summary
    ds_client_mock.get_recipients.return_value = recipients

    payload = {
        "signers": [
            {
                "recipientId": "1",
                "email": SIGNER1_EMAIL,
                "name": SIGNER1_NAME,
            },
        ],
    }

    app_container.esign_recipients_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.put(
            f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/signers",
            json=payload,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "envelopeId": pre_stored_envelopes["envelope_sent"].envelope_id,
            "signers": [
                {
                    "recipientIdGuid": SIGNER1_GUID,
                    "recipientId": "1",
                    "email": SIGNER1_EMAIL,
                    "name": SIGNER1_NAME,
                    "updateError": None,
                },
            ],
        }


@pytest.mark.asyncio
async def test_should_return404_on_non_existing_envelope_in_db(
    client: AsyncClient,
    app_container: Container,
    mock_docusign_api_client,
):
    envelope_id = "abcde512-f63d-40e4-ab49-4c0eb5c99c5e"

    app_container.esign_recipients_service.reset()
    response = await client.put(
        f"/api/v1/esign/envelope/{envelope_id}/signers",
        json={
            "signers": [
                {
                    "recipientId": "1",
                    "email": SIGNER1_EMAIL,
                    "name": SIGNER1_NAME,
                },
            ],
        },
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist in database",
            "field": "envelopeId",
            "value": envelope_id,
        },
    }


@pytest.mark.asyncio
async def test_should_return404_on_non_existing_envelope(
    client: AsyncClient,
    app_container: Container,
    mocker: MockerFixture,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    api_exc = ApiException(status=status.HTTP_404_NOT_FOUND, reason=HTTPStatus.NOT_FOUND.phrase)
    api_exc.body = json.dumps({"errorCode": ExcErrorCodeEnum.envelope_does_not_exist.value})

    mocker.patch("docusign_esign.EnvelopesApi.update_recipients", side_effect=api_exc)

    payload = {
        "signers": [
            {
                "recipientId": "1",
                "email": SIGNER1_EMAIL,
                "name": SIGNER1_NAME,
            },
        ],
    }

    app_container.esign_recipients_service.reset()
    response = await client.put(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/signers",
        json=payload,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_sent"].envelope_id,
        },
    }


@pytest.mark.asyncio
async def test_should_return400_on_completed_envelope(
    client: AsyncClient,
    app_container: Container,
    mocker: MockerFixture,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    api_exc = ApiException(status=status.HTTP_400_BAD_REQUEST, reason=HTTPStatus.BAD_REQUEST.phrase)
    api_exc.body = json.dumps({"errorCode": ExcErrorCodeEnum.envelope_invalid_status.value})

    mocker.patch("docusign_esign.EnvelopesApi.update_recipients", side_effect=api_exc)

    payload = {
        "signers": [
            {
                "recipientId": "1",
                "email": SIGNER1_EMAIL,
                "name": SIGNER1_NAME,
            },
        ],
    }
    app_container.esign_recipients_service.reset()
    response = await client.put(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/signers",
        json=payload,
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message":
                "Signers can be changed only for envelope in the "
                + "'Created', 'Sent', 'Delivered', 'Correct' status",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_sent"].envelope_id,
        }
    }


@pytest.mark.asyncio
async def test_should_return400_on_all_recipients_update_failed(
    client: AsyncClient,
    app_container: Container,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    recipient_update_summary = RecipientsUpdateSummary(
        recipient_update_results=[
            RecipientUpdateResponse(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                error_details=ErrorDetails(message=ERROR_DETAILS),
            ),
            RecipientUpdateResponse(
                recipient_id="2",
                recipient_id_guid=SIGNER1_GUID,
                error_details=ErrorDetails(message=ERROR_DETAILS),
            ),
        ],
    )
    recipients = Recipients(
        signers=[
            Signer(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                email=SIGNER1_EMAIL,
                name=SIGNER1_NAME,
            ),
            Signer(
                recipient_id="2",
                recipient_id_guid=SIGNER2_GUID,
                email=SIGNER2_EMAIL,
                name=SIGNER2_NAME,
            ),
        ],
    )
    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.update_recipients.return_value = recipient_update_summary
    ds_client_mock.get_recipients.return_value = recipients

    payload = {
        "signers": [
            {
                "recipientId": "1",
                "email": SIGNER1_EMAIL,
                "name": SIGNER1_NAME,
            },
            {
                "recipientId": "2",
                "email": SIGNER2_EMAIL,
                "name": SIGNER2_NAME,
            },
        ],
    }

    app_container.esign_recipients_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.put(
            f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/signers",
            json=payload,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {
            "detail": {
                "message": "All recipient in the state that doesn't allows correction.",
                "field": "envelopeId",
                "value": pre_stored_envelopes["envelope_sent"].envelope_id,
            },
        }


@pytest.mark.asyncio
async def test_should_return200_on_partial_successful_update(
    client: AsyncClient,
    app_container: Container,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    recipient_update_summary = RecipientsUpdateSummary(
        recipient_update_results=[
            RecipientUpdateResponse(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                error_details=ErrorDetails(message=ERROR_DETAILS),
            ),
            RecipientUpdateResponse(
                recipient_id="2",
                recipient_id_guid=SIGNER1_GUID,
                error_details=None,
            ),
        ],
    )
    recipients = Recipients(
        signers=[
            Signer(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                email=SIGNER1_EMAIL,
                name=SIGNER1_NAME,
            ),
            Signer(
                recipient_id="2",
                recipient_id_guid=SIGNER2_GUID,
                email=SIGNER2_EMAIL,
                name=SIGNER2_NAME,
            ),
        ],
    )
    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.update_recipients.return_value = recipient_update_summary
    ds_client_mock.get_recipients.return_value = recipients

    payload = {
        "signers": [
            {
                "recipientId": "1",
                "email": SIGNER1_EMAIL,
                "name": SIGNER1_NAME,
            },
            {
                "recipientId": "2",
                "email": SIGNER2_EMAIL,
                "name": SIGNER2_NAME,
            },
        ],
    }

    app_container.esign_recipients_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.put(
            f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/signers",
            json=payload,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {
            "envelopeId": pre_stored_envelopes["envelope_sent"].envelope_id,
            "signers": [
                {
                    "recipientIdGuid": SIGNER1_GUID,
                    "recipientId": "1",
                    "email": SIGNER1_EMAIL,
                    "name": SIGNER1_NAME,
                    "updateError": ERROR_DETAILS,
                },
                {
                    "recipientIdGuid": SIGNER2_GUID,
                    "recipientId": "2",
                    "email": SIGNER2_EMAIL,
                    "name": SIGNER2_NAME,
                    "updateError": None,
                },
            ],
        }


@pytest.mark.asyncio
async def test_should_return400_on_envelope_in_crating_state(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    app_container.esign_recipients_service.reset()
    response = await client.put(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_creating'].envelope_id}/signers",
        json={
            "signers": [
                {
                    "recipientId": "1",
                    "email": SIGNER1_EMAIL,
                    "name": SIGNER1_NAME,
                },
            ],
        },
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Actions with the document in the custom:creating status are prohibited",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_creating"].envelope_id,
        }
    }
