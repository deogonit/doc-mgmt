import json
import uuid
from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest
from docusign_esign import ApiException, EnvelopeUpdateSummary
from fastapi import status
from httpx import AsyncClient
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import ExcErrorCodeEnum
from app.esign.models.envelope import EnvelopePutItem


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post(
        "/api/v1/esign/envelope/123/resend",
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
async def test_should_return200_on_resend_envelope(
    client: AsyncClient,
    app_container: Container,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.update_envelope.return_value = EnvelopeUpdateSummary(
        envelope_id=pre_stored_envelopes["envelope_sent"].envelope_id
    )

    app_container.esign_envelope_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.post(
            f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/resend",
        )

        assert response.status_code == status.HTTP_200_OK
        assert uuid.UUID(response.json()["envelopeId"])


@pytest.mark.asyncio
async def test_should_return404_on_not_existing_envelope_in_db(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
):
    envelope_id = "abcde512-f63d-40e4-ab49-4c0eb5c99c5d"

    app_container.esign_envelope_service.reset()
    response = await client.post(
        f"/api/v1/esign/envelope/{envelope_id}/resend",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist in database",
            "field": "envelopeId",
            "value": envelope_id,
        }
    }


@pytest.mark.asyncio
async def test_should_return404_on_not_existing_envelope(
    app_container: Container,
    mocker: MockerFixture,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    api_exc = ApiException(status=status.HTTP_404_NOT_FOUND, reason=HTTPStatus.NOT_FOUND.phrase)
    api_exc.body = json.dumps({"errorCode": ExcErrorCodeEnum.envelope_does_not_exist.value})
    mocker.patch("docusign_esign.EnvelopesApi.update", side_effect=api_exc)

    app_container.esign_envelope_service.reset()
    response = await client.post(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/resend",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_sent"].envelope_id,
        }
    }


@pytest.mark.asyncio
async def test_should_return400_on_invalid_envelope_state(
    app_container: Container,
    mocker: MockerFixture,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    api_exc = ApiException(status=status.HTTP_400_BAD_REQUEST, reason=HTTPStatus.BAD_REQUEST.phrase)
    api_exc.body = json.dumps({"errorCode": ExcErrorCodeEnum.resend_invalid_state.value})
    mocker.patch("docusign_esign.EnvelopesApi.update", side_effect=api_exc)

    app_container.esign_envelope_service.reset()
    response = await client.post(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/resend",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Only envelope in the 'Created', 'Sent' or 'Delivered' states may be resent.",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_sent"].envelope_id,
        }
    }


@pytest.mark.asyncio
async def test_should_return400_on_envelope_in_crating_state(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    app_container.esign_envelope_service.reset()
    response = await client.post(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_creating'].envelope_id}/resend",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Actions with the document in the custom:creating status are prohibited",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_creating"].envelope_id,
        }
    }
