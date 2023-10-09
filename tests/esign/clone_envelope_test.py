import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import docusign_esign
import pytest
import pytest_asyncio
from fastapi import status
from httpx import AsyncClient

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.models.envelope import DocumentItem, EnvelopeDeleteItem, EnvelopePutItem, SignerItem
from app.esign.models.envelope_callback import EnvelopeCallbackPutItem, EnvelopeCallbackSearchItem
from app.esign.repositories import EnvelopeCallbackRepository

DEFAULT_ENVELOPE_ID = "abcde512-f63d-40e4-ab49-4c0eb5c99c5c"

SIGNER1_GUID = "3970c7c4-41e8-4dce-82c3-0c50470f2516"
SIGNER1_EMAIL = "signer1@email.example"
SIGNER1_NAME = "Signer 1 Name"

SIGNER2_GUID = "64cd3b06-a7d2-4523-b417-a56c590c54db"
SIGNER2_EMAIL = "signer2@email.example"
SIGNER2_NAME = "Signer 2 Name"


@pytest_asyncio.fixture(scope="function")
async def envelope_stored_in_db(
    app_container: Container,
    main_bucket_name: str,
) -> AsyncGenerator[None, None]:
    envelope_put_item = EnvelopePutItem(
        envelope_id=DEFAULT_ENVELOPE_ID,
        envelope_status=EnvelopeStatusEnum.declined.value,
        status_changed_date_time="2022-12-07T13:50:35.08Z",
        expiration_time=None,
        signers=[
            SignerItem(
                email=SIGNER1_EMAIL,
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                status=EnvelopeStatusEnum.completed.value,
            ),
            SignerItem(
                email=SIGNER2_EMAIL,
                recipient_id="2",
                recipient_id_guid=SIGNER2_GUID,
                status=EnvelopeStatusEnum.declined.value,
            )
        ],
        documents=[
            DocumentItem(
                document_id="1",
                document_id_guid=str(uuid.uuid4()),
                name="Document name",
                uri=f"envelopes/{DEFAULT_ENVELOPE_ID}/1",
                order=1,
                document_bucket_name=main_bucket_name,
                document_path="templates/esign.pdf",
            )
        ]
    )

    repository = await app_container.envelope_repository()  # type: ignore
    await repository.put_item(envelope_put_item)

    yield

    await repository.delete_item(EnvelopeDeleteItem(envelope_id=envelope_put_item.envelope_id))


def build_docusign_envelope_definition() -> docusign_esign.EnvelopeDefinition:
    return docusign_esign.EnvelopeDefinition(
        envelope_id=DEFAULT_ENVELOPE_ID,
        status=EnvelopeStatusEnum.declined.value,
        email_subject="Email subject",
        email_blurb="Email body",
        documents=[
            docusign_esign.Document(
                document_id="1",
                name="Document name",
                document_base64="veryshortfilecontent",
                file_extension="pdf",
            )
        ],
        recipients=docusign_esign.Recipients(signers=[
            docusign_esign.Signer(
                recipient_id="1",
                recipient_id_guid=SIGNER1_GUID,
                email=SIGNER1_EMAIL,
                name=SIGNER1_NAME,
                routing_order="1",
            ),
            docusign_esign.Signer(
                recipient_id="2",
                recipient_id_guid=SIGNER2_GUID,
                email=SIGNER2_EMAIL,
                name=SIGNER2_NAME,
                routing_order="2",
            ),
        ]),
    )


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post(
        "/api/v1/esign/envelope/123/clone",
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
async def test_should_return200_on_clone_envelope(  # noqa: WPS218
    client: AsyncClient,
    app_container: Container,
    envelope_stored_in_db: dict,
):
    env_def = build_docusign_envelope_definition()

    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.get_envelope.return_value = env_def
    ds_client_mock.create_envelope = AsyncMock(
        return_value=docusign_esign.EnvelopeSummary(envelope_id=str(uuid.uuid4()))
    )

    app_container.esign_envelope_create_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.post(
            f"/api/v1/esign/envelope/{DEFAULT_ENVELOPE_ID}/clone",
        )

        assert response.status_code == status.HTTP_200_OK
        assert uuid.UUID(response.json()["envelopeId"])

        called_env_def: docusign_esign.EnvelopeDefinition = ds_client_mock.create_envelope.call_args[0][0]

        assert called_env_def.status == EnvelopeStatusEnum.sent.value
        assert called_env_def.email_subject == env_def.email_subject
        assert called_env_def.email_blurb == env_def.email_blurb

        assert 1 == len(called_env_def.documents) == len(env_def.documents)
        assert called_env_def.documents[0].name == env_def.documents[0].name

        assert len(called_env_def.recipients.signers) == 1
        assert "2" == called_env_def.recipients.signers[0].recipient_id == env_def.recipients.signers[1].recipient_id
        assert SIGNER2_EMAIL == called_env_def.recipients.signers[0].email == env_def.recipients.signers[1].email
        assert SIGNER2_NAME == called_env_def.recipients.signers[0].name == env_def.recipients.signers[1].name


@pytest.mark.asyncio
async def test_should_return200_store_envelope_callback(
    client: AsyncClient,
    app_container: Container,
    envelope_stored_in_db: dict,
    envelope_callback_repository: EnvelopeCallbackRepository,
):
    env_def = build_docusign_envelope_definition()

    await envelope_callback_repository.put_item(EnvelopeCallbackPutItem(
        envelope_id=DEFAULT_ENVELOPE_ID,
        callback_url="callback.com",
        expiration_time=None,
    ))

    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.get_envelope.return_value = env_def
    ds_client_mock.create_envelope = AsyncMock(
        return_value=docusign_esign.EnvelopeSummary(envelope_id=str(uuid.uuid4()))
    )

    app_container.esign_envelope_create_service.reset()
    with app_container.docusign_client.override(ds_client_mock):
        response = await client.post(
            f"/api/v1/esign/envelope/{DEFAULT_ENVELOPE_ID}/clone",
        )

        assert response.status_code == status.HTTP_200_OK

        resp_envelope_id = response.json()["envelopeId"]
        assert uuid.UUID(resp_envelope_id)

        envelope_callback = await envelope_callback_repository.get_item(
            EnvelopeCallbackSearchItem(envelope_id=resp_envelope_id)
        )
        assert envelope_callback is not None

        # await envelope_callback_repository.delete_item(EnvelopeCallbackDeleteItem(envelope_id=resp_envelope_id))


@pytest.mark.asyncio
async def test_should_return400_on_envelope_in_crating_state(
    app_container: Container,
    client: AsyncClient,
    mock_docusign_api_client,
    pre_stored_envelopes: dict[str, EnvelopePutItem],
):
    app_container.esign_envelope_create_service.reset()
    response = await client.post(
        f"/api/v1/esign/envelope/{pre_stored_envelopes['envelope_creating'].envelope_id}/clone",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Actions with the document in the custom:creating status are prohibited",
            "field": "envelopeId",
            "value": pre_stored_envelopes["envelope_creating"].envelope_id,
        }
    }
