import uuid
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest
import pytest_asyncio
from pytest_mock import MockerFixture

from app.container import Container
from app.esign.enum import EnvelopeStatusEnum
from app.esign.models.envelope import DocumentItem, EnvelopeDeleteItem, EnvelopePutItem, SignerItem
from app.esign.repositories.envelope import EnvelopeRepository
from app.esign.repositories.envelope_callback import EnvelopeCallbackRepository
from app.esign.schema.envelope import (
    DSDocumentRequest,
    DSEnvelopeRequest,
    DSSignerRequest,
    TabsRequest,
)
from app.esign.schema.tab import DSInitialHereTab
from app.esign.services import ESignEnvelopeService
from app.file_storage.service import FileStorageService

ANCHOR_Y_OFFSET = 40
ANCHOR_X_OFFSET = 20


@pytest_asyncio.fixture(scope="session")
async def storage_service(app_container: Container) -> FileStorageService:
    return await app_container.storage_service()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def esign_envelope_service(app_container: Container) -> ESignEnvelopeService:
    return await app_container.esign_envelope_service()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def esign_envelope_create_service(app_container: Container) -> ESignEnvelopeService:
    return await app_container.esign_envelope_create_service()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def envelope_repository(app_container: Container) -> EnvelopeRepository:
    return await app_container.envelope_repository()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def envelope_callback_repository(app_container: Container) -> EnvelopeCallbackRepository:
    return await app_container.envelope_callback_repository()  # type: ignore


@pytest_asyncio.fixture(scope="function")
def valid_envelope_schema(main_bucket_name: str):
    yield DSEnvelopeRequest(
        email_subject="Please sign this document",
        email_body="This is a body",
        documents=[
            DSDocumentRequest(
                document_id=1,
                name="Main document",
                bucketName=main_bucket_name,
                document_path="templates/esign.pdf"
            )
        ],
        signers=[
            DSSignerRequest(
                recipient_id=1,
                email="cesigntest@gmail.com",
                name="Odin Borson",
                order=1,
                email_subject="Odin Borson, please sign this document",
                emailBody="This is the best and the most important document\nfor Signer 1.\n\nBest wishes.",
                tabs=TabsRequest(
                    initial_here_tabs=[
                        DSInitialHereTab(
                            anchor_string="/sn1/",
                            anchor_units="pixels",
                            anchor_x_offset=ANCHOR_X_OFFSET,
                            anchor_y_offset=ANCHOR_Y_OFFSET,
                        ),
                    ],
                ),
            ),
        ],
    )


async def _mock_store_signed_documents_in_bucket(self, envelope_id: str, documents: list[DocumentItem]):
    return documents


@pytest_asyncio.fixture(scope="function")
async def mock_store_signed_documents_in_bucket(mocker: MockerFixture) -> AsyncGenerator:
    mocker.patch(
        "app.esign.services.ESignWebhookService._store_signed_documents_in_bucket",
        _mock_store_signed_documents_in_bucket,
    )

    yield


@pytest.fixture(scope="function")
def mock_docusign_api_client(mocker: MockerFixture) -> Generator:
    mocker.patch("docusign_esign.ApiClient.request_jwt_user_token", Mock())

    yield


@pytest_asyncio.fixture(scope="function")
async def pre_stored_envelopes(app_container: Container):
    envelope_creating = EnvelopePutItem(
        envelope_id=str(uuid.uuid4()),
        envelope_status=EnvelopeStatusEnum.custom_creating.value,
        status_changed_date_time="2022-12-07T13:50:35.08Z",
        expiration_time=None,
    )

    sent_envelope_id = str(uuid.uuid4())
    envelope_sent = EnvelopePutItem(
        envelope_id=sent_envelope_id,
        envelope_status=EnvelopeStatusEnum.sent.value,
        expiration_time=None,
        status_changed_date_time="2022-12-07T13:50:35.08Z",
        signers=[
            SignerItem(
                email="signer1@example.com",
                recipient_id="1",
                recipient_id_guid=str(uuid.uuid4()),
                status=EnvelopeStatusEnum.sent.value,
            )
        ],
        documents=[
            DocumentItem(
                document_id="1",
                document_id_guid=str(uuid.uuid4()),
                name="Main name",
                uri=f"envelopes/{sent_envelope_id}/1",
                order=1,
            )
        ]
    )

    repository = await app_container.envelope_repository()  # type: ignore
    await repository.put_item(envelope_creating)
    await repository.put_item(envelope_sent)

    yield {
        "envelope_creating": envelope_creating,
        "envelope_sent": envelope_sent,
    }

    await repository.delete_item(EnvelopeDeleteItem(envelope_id=envelope_creating.envelope_id))
    await repository.delete_item(EnvelopeDeleteItem(envelope_id=envelope_sent.envelope_id))
