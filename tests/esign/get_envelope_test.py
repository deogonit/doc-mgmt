from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.models.envelope import EnvelopePutItem


@pytest_asyncio.fixture(scope="module", autouse=True)
async def docusign_client_mock(
    app_container: Container,
) -> AsyncGenerator[None, None]:

    ds_client_mock = AsyncMock(spec=DocuSignClient)

    with app_container.docusign_client.override(ds_client_mock):
        yield


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.get("/api/v1/esign/envelope/123", headers={"Authorization": "rand"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return200_and_should_with_envelope(
    client: AsyncClient,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    envelope_id = pre_stored_envelopes["envelope_sent"].envelope_id

    response = await client.get(f"/api/v1/esign/envelope/{envelope_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "envelopeId": envelope_id,
        "envelopeStatus": "sent",
        "statusChangedDateTime": "2022-12-07T13:50:35.080000+00:00",
        "signers": [
            {
                "recipientId": pre_stored_envelopes["envelope_sent"].signers[0].recipient_id,  # type: ignore
                "recipientIdGuid": pre_stored_envelopes["envelope_sent"].signers[0].recipient_id_guid,  # type: ignore
                "email": "signer1@example.com",
                "status": "sent"
            },
        ],
        "documents": [
            {
                "documentId": "1",
                "documentIdGuid": pre_stored_envelopes["envelope_sent"].documents[0].document_id_guid,  # type: ignore
                "name": "Main name",
                "order": 1,
                "uri": f"envelopes/{envelope_id}/1",
                "documentPath": None,
                "documentBucketName": None,
            }
        ]
    }


@pytest.mark.asyncio
async def test_should_return200_on_envelope_in_crating_state(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    response = await client.get(f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_creating'].envelope_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "envelopeId": pre_stored_envelopes["envelope_creating"].envelope_id,
        "envelopeStatus": EnvelopeStatusEnum.custom_creating.value,
        "statusChangedDateTime": pre_stored_envelopes["envelope_creating"].status_changed_date_time.isoformat(),
        "signers": None,
        "documents": None,
    }


@pytest.mark.asyncio
async def test_should_return404_on_no_envelope(client: AsyncClient):
    response = await client.get("/api/v1/esign/envelope/12345")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Envelop by id does not exist in database",
            "field": "envelopeId",
            "value": "12345"
        }
    }
