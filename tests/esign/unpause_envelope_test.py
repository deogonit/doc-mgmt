import json
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
    response = await client.patch(
        "/api/v1/esign/envelope/123/unpause",
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
async def test_should_return200_on_unpause_envelope(
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
        response = await client.patch(
            f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/unpause",
        )

        assert response.status_code == status.HTTP_200_OK
        assert not response.json()  # response.json() == {}


@pytest.mark.asyncio
async def test_should_return404_on_not_existing_envelope_in_db(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
):
    envelope_id = "abcde512-f63d-40e4-ab49-4c0eb5c99c5d"

    app_container.esign_envelope_service.reset()
    response = await client.patch(
        f"/api/v1/esign/envelope/{envelope_id}/unpause",
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
    response = await client.patch(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_sent'].envelope_id}/unpause",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_sent"].envelope_id,
        }
    }
