import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from docusign_esign import EnvelopeSummary
from httpx import AsyncClient
from starlette import status

from app.container import Container
from app.esign.client import DocuSignClient
from app.esign.models.envelope_callback import EnvelopeCallbackSearchItem
from app.esign.repositories.envelope_callback import EnvelopeCallbackRepository
from app.esign.schema.envelope import DSEnvelopeRequest
from app.esign.services.envelope_create import ESignEnvelopeCreateService
from tests.esign.constants import EMAIL_SUBJECT, REQUEST_WITH_ALL_TABS


@pytest_asyncio.fixture(scope="function", autouse=True)
async def docusign_client_mock(
    app_container: Container,
) -> AsyncGenerator[None, None]:

    ds_client_mock = AsyncMock(spec=DocuSignClient)
    ds_client_mock.create_envelope.return_value = EnvelopeSummary(envelope_id=str(uuid.uuid4()))

    with app_container.docusign_client.override(ds_client_mock):
        yield


@pytest_asyncio.fixture(scope="function")
def valid_payload(main_bucket_name: str):
    yield {
        EMAIL_SUBJECT: EMAIL_SUBJECT,
        "documents": [
            {
                "documentId": 1,
                "name": "Main document",
                "bucketName": main_bucket_name,
                "documentPath": "templates/esign.pdf",
            }
        ],
        "signers": [
            {
                "recipientId": 1,
                "email": "cesigntest@gmail.com",
                "name": "Odin Borson",
                "order": 1,
                EMAIL_SUBJECT: EMAIL_SUBJECT,
            }
        ],
    }


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post("/api/v1/esign/envelope", json={}, headers={"Authorization": "rand"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return200_on_create_envelope(
    client: AsyncClient,
    app_container: Container,
    valid_envelope_schema: DSEnvelopeRequest,
    envelope_callback_repository: EnvelopeCallbackRepository
):

    app_container.esign_envelope_create_service.reset()
    response = await client.post("/api/v1/esign/envelope", json=valid_envelope_schema.dict())

    envelope_id = response.json()["envelopeId"]
    envelope_callback = await envelope_callback_repository.get_item(EnvelopeCallbackSearchItem(envelope_id=envelope_id))

    assert response.status_code == status.HTTP_200_OK
    assert uuid.UUID(envelope_id)
    assert envelope_callback is None


@pytest.mark.asyncio
async def test_should_return200_on_create_envelope_without_tabs(
    client: AsyncClient,
    app_container: Container,
    valid_envelope_schema: DSEnvelopeRequest,
):
    updated_schema = valid_envelope_schema.dict()
    updated_schema["signers"][0]["tabs"] = None

    app_container.esign_envelope_create_service.reset()
    response = await client.post("/api/v1/esign/envelope", json=updated_schema)

    envelope_id = response.json()["envelopeId"]

    assert response.status_code == status.HTTP_200_OK
    assert uuid.UUID(envelope_id)


@pytest.mark.asyncio
async def test_should_return200_create_envelope_and_save_callback_url(
    client: AsyncClient,
    app_container: Container,
    valid_envelope_schema: DSEnvelopeRequest,
    envelope_callback_repository: EnvelopeCallbackRepository,
):
    callback_url = "https://www.lipsum.com/"
    request_data = valid_envelope_schema.dict() | {"callbackUrl": callback_url}

    app_container.esign_envelope_create_service.reset()
    response = await client.post("/api/v1/esign/envelope", json=request_data)

    envelope_id = response.json()["envelopeId"]
    envelope_callback = await envelope_callback_repository.get_item(EnvelopeCallbackSearchItem(envelope_id=envelope_id))

    assert response.status_code == status.HTTP_200_OK
    assert uuid.UUID(envelope_id)
    assert envelope_callback is not None
    assert envelope_callback.callback_url == callback_url


@pytest.mark.asyncio
@pytest.mark.parametrize("payload, expected_error", [
    # Case 1: Missing email subject field
    (
        {
            "documents": [
                {
                    "documentId": 1,
                    "name": "Main document",
                    "bucketName": "main_bucket_name",
                    "documentPath": "templates/esign.pdf",
                }
            ],
            "signers": [
                {
                    "recipientId": 1,
                    "email": "cesigntest@gmail.com",
                    "name": "Odin Borson",
                    "order": 1,
                    EMAIL_SUBJECT: EMAIL_SUBJECT,
                }
            ],
        },
        {
            "detail": [
                {
                    "message": "field required",
                    "field": EMAIL_SUBJECT,
                    "type": "value_error.missing",
                }
            ]
        }
    ),
    # Case 2: Should be provided document and signer object
    (
        {
            EMAIL_SUBJECT: EMAIL_SUBJECT,
            "documents": [],
            "signers": [],
        },
        {
            "detail": [
                {
                    "message": "At least one document has to be provided",
                    "field": "documents",
                    "type": "value_error",
                },
                {
                    "message": "At least one signer has to be provided",
                    "field": "signers",
                    "type": "value_error",
                }
            ]
        }
    ),
    # Case 3: Should be valid email address
    (
        {
            EMAIL_SUBJECT: EMAIL_SUBJECT,
            "documents": [
                {
                    "documentId": 1,
                    "name": "Main document",
                    "bucketName": "main_bucket_name",
                    "documentPath": "templates/esign.pdf",
                }
            ],
            "signers": [
                {
                    "recipientId": 1,
                    "email": "any_string",
                    "name": "Odin Borson",
                    "order": 1,
                    EMAIL_SUBJECT: EMAIL_SUBJECT,
                }
            ],
        },
        {
            "detail": [
                {
                    "message": "value is not a valid email address",
                    "field": "signers.0.email",
                    "type": "value_error.email"
                }
            ]
        }
    ),
    # Case 4: Should be valid size
    (
        {
            EMAIL_SUBJECT: EMAIL_SUBJECT,
            "documents": [
                {
                    "documentId": 1,
                    "name": "Main document",
                    "bucketName": "main_bucket_name",
                    "documentPath": "templates/esign.pdf",
                }
            ],
            "signers": [
                {
                    "recipientId": 1,
                    "email": "cesigntest@gmail.com",
                    "name": "Odin Borson",
                    "order": 1,
                    "tabs": {
                        "textTabs": [{"fontSize": "12"}]
                    },
                    EMAIL_SUBJECT: EMAIL_SUBJECT,
                }
            ],
        },
        {
            "detail": [
                {
                    "message": 'string does not match regex "^size\\d{1,3}$"',  # noqa: WPS342
                    "field": "signers.0.tabs.textTabs.0.fontSize",
                    "type": "value_error.str.regex",
                }
            ]
        }
    ),
    # Case 5: Email subject should have correct length
    (
        {
            EMAIL_SUBJECT: EMAIL_SUBJECT,
            "documents": [
                {
                    "documentId": 1,
                    "name": "Main document",
                    "bucketName": "main_bucket_name",
                    "documentPath": "templates/esign.pdf",
                }
            ],
            "signers": [
                {
                    "recipientId": 1,
                    "email": "cesigntest@gmail.com",
                    "name": "Odin Borson",
                    "order": 1,
                    EMAIL_SUBJECT: "email subject " * 10,
                }
            ],
        },
        {
            "detail": [
                {
                    "message": "ensure this value has at most 100 characters",
                    "field": "signers.0.emailSubject",
                    "type": "value_error.any_str.max_length",
                }
            ]
        }
    )
])
async def test_should_return422_on_validation_error(
    client: AsyncClient,
    app_container: Container,
    payload: dict,
    expected_error: dict,
):
    app_container.esign_envelope_create_service.reset()
    response = await client.post("/api/v1/esign/envelope", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == expected_error


@pytest.mark.asyncio
async def test_should_return404_on_non_existing_document(
    client: AsyncClient,
    app_container: Container,
    main_bucket_name: str,
):
    file_dont_exists_pdf = "file_dont_exists.pdf"
    payload = {
        EMAIL_SUBJECT: EMAIL_SUBJECT,
        "documents": [
            {
                "documentId": 1,
                "name": "Main document",
                "bucketName": main_bucket_name,
                "documentPath": file_dont_exists_pdf,
            }
        ],
        "signers": [
            {
                "recipientId": 1,
                "email": "cesigntest@gmail.com",
                "name": "Odin Borson",
                "order": 1,
                EMAIL_SUBJECT: EMAIL_SUBJECT,
            }
        ],
    }

    app_container.esign_envelope_create_service.reset()
    response = await client.post("/api/v1/esign/envelope", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "Document by path does not exist",
            "field": "documentPath",
            "value": file_dont_exists_pdf,
        }
    }


@pytest.mark.asyncio
async def test_should_create_envelope_with_all_tabs(
    esign_envelope_create_service: ESignEnvelopeCreateService,
    main_bucket_name: str,
):
    valid_envelope_schema = DSEnvelopeRequest(**REQUEST_WITH_ALL_TABS)
    valid_envelope_schema.documents[0].bucket_name = main_bucket_name

    envelope_definition = await esign_envelope_create_service.build_envelope_definition(valid_envelope_schema)

    assert len(envelope_definition.documents) == 1
    assert len(envelope_definition.recipients.signers) == 2

    first_signer = envelope_definition.recipients.signers[0]
    second_signer = envelope_definition.recipients.signers[0]

    assert [
        len(first_signer.tabs.initial_here_tabs),
        len(first_signer.tabs.sign_here_tabs),
        len(first_signer.tabs.full_name_tabs),
        len(first_signer.tabs.text_tabs),
        len(first_signer.tabs.email_tabs),
        len(first_signer.tabs.title_tabs),
        len(first_signer.tabs.date_tabs),
        len(first_signer.tabs.checkbox_tabs),
        len(first_signer.tabs.number_tabs),
        len(first_signer.tabs.list_tabs),
        len(first_signer.tabs.radio_group_tabs),
        len(second_signer.tabs.sign_here_tabs),
    ] == [2, 1, 1, 4, 1, 1, 1, 1, 1, 1, 1, 1]


@pytest.mark.asyncio
async def test_should_create_envelope_definition_with_all_provided_data(
    esign_envelope_create_service: ESignEnvelopeCreateService,
    valid_envelope_schema: DSEnvelopeRequest
):
    envelope_definition = await esign_envelope_create_service.build_envelope_definition(valid_envelope_schema)

    assert [
        envelope_definition.email_subject,
        envelope_definition.email_blurb,
    ] == [
        valid_envelope_schema.email_subject,
        valid_envelope_schema.email_body,
    ]

    document_definition = envelope_definition.documents[0]
    assert [
        document_definition.document_id,
        document_definition.name,
        document_definition.file_extension
    ] == [
        valid_envelope_schema.documents[0].document_id,
        valid_envelope_schema.documents[0].name,
        "pdf"
    ]
    assert document_definition.document_base64

    signer_definition = envelope_definition.recipients.signers[0]
    signer_schema = valid_envelope_schema.signers[0]

    assert [
        signer_definition.recipient_id,
        signer_definition.email,
        signer_definition.name,
        signer_definition.routing_order,
        signer_definition.email_notification.email_subject,
        signer_definition.email_notification.email_body
    ] == [
        signer_schema.recipient_id,
        signer_schema.email,
        signer_schema.name,
        signer_schema.order,
        signer_schema.email_subject,
        signer_schema.email_body
    ]

    initial_here_tab_definition = signer_definition.tabs.initial_here_tabs[0]
    initial_here_tab_schema = signer_schema.tabs.initial_here_tabs[0]  # type: ignore

    assert [
        initial_here_tab_definition.anchor_string,
        initial_here_tab_definition.anchor_units,
        initial_here_tab_definition.anchor_units,
        initial_here_tab_definition.anchor_x_offset,
        initial_here_tab_definition.anchor_y_offset,
    ] == [
        initial_here_tab_schema.anchor_string,
        initial_here_tab_schema.anchor_units,
        initial_here_tab_schema.anchor_units,
        initial_here_tab_schema.anchor_x_offset,
        initial_here_tab_schema.anchor_y_offset,
    ]
