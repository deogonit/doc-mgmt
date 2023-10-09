from io import BytesIO

import pytest
from fastapi import status
from httpx import AsyncClient
from pypdf import PdfReader

from app.file_storage.service import FileStorageService
from tests.constants import SIGNATURE_IMAGE, TEMPLATE4_DOCX


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post("/api/v1/doc-generation/merge", json={}, headers={"Authorization": "rand"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return422_on_invalid_template_extension(client: AsyncClient):
    payload = {
        "bucketName": "any-name",
        "templatePaths": ["sub_dir/doc.txt", "sub_dir/doc.ppf"],
        "templateVariables": {}
    }
    response = await client.post("/api/v1/doc-generation/merge", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {
        "detail": [
            {
                "message":
                    "Invalid templates: ['sub_dir/doc.txt', 'sub_dir/doc.ppf']. "
                    + "Template path should have these ext: ['.docx', '.pdf', '.html']",
                "field": "templatePaths",
                "type": "value_error"
            }
        ]
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary_payload",
    [
        {
            "templatePaths": ["templates/template_1.docx", "templates/google.pdf"],
            "templateVariables": {
                "policy_number_al": 12345,
            }
        },
        {
            "templatePaths": [
                "templates/template_1.docx",
                "templates/template_2.docx",
                "templates/google.pdf",
                "templates/form.pdf",
                f"templates/{TEMPLATE4_DOCX}",
            ],
            "templateVariables": {
                "policy_number_al": 12345,
                "legal_name": "Friends",
                "dba_name": "LLC",
                "mailing_street": "90 Bedford St",
                "mailing_city": "New York",
                "mailing_state": "NY",
                "mailing_zip": "10014",
                "effective_date": "October 7, 2022 08:40:26 EST",
                "expiration_date": "October 7, 2023 08:40:26 EST",
                "tgl_rate": "650.10",
                "carrier_al_name": "Company NAME",
                "producer_name": "Producer NAME",
                "effective_date_transaction": "September 27, 2023",
                "expiration_date_transaction": "September 27, 2024",
                "entity_type": "Form Of Business",
                "total_premium_endorsements_al_total": "$13,961.41",
                "form_title": "Form Title",
                "form_number": "Form Number",
                "form_edition": "Form Edition",
                "signature_name": "Signature Name",
                "signature_title": "Signature Title",
            },
            "images": [
                {
                    "variable_name": "signature_img",
                    "image_path": f"images/{SIGNATURE_IMAGE}",
                    "width": 50,
                    "height": 25
                }
            ],
        }
    ],
)
async def test_should_return200_and_convert_template_and_merge_documents(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
    primary_payload,
):
    payload = primary_payload | {"bucketName": main_bucket_name}
    response = await client.post("/api/v1/doc-generation/merge", json=payload)

    file_path = response.json()["documentPath"]
    obj_file = await storage_service.get_object(main_bucket_name, file_path)
    assert obj_file is not None
    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)

    assert response.status_code == status.HTTP_200_OK
    assert file_path.startswith("documents/")
    assert file_path.endswith(".pdf")
    assert len(pdf_reader.pages) == len(primary_payload["templatePaths"])


@pytest.mark.asyncio
async def test_should_return200_and_convert_templates_and_merge_once_if_with_same_request(
    client: AsyncClient,
    main_bucket_name: str,
):
    payload = {
        "bucketName": main_bucket_name,
        "templatePaths": [
            "templates/template_1.docx",
            "templates/template_2.docx",
            "templates/google.pdf",
        ],
        "templateVariables": {
            "policy_number_al": 12345,
            "legal_name": "Friends",
            "dba_name": "LLC",
            "mailing_street": "90 Bedford St",
            "mailing_city": "New York",
            "mailing_state": "NY",
            "mailing_zip": "10014",
            "effective_date": "October 7, 2022 08:40:26 EST",
            "expiration_date": "October 7, 2023 08:40:26 EST",
        }
    }

    first_response = await client.post("/api/v1/doc-generation/merge", json=payload)
    second_response = await client.post("/api/v1/doc-generation/merge", json=payload)

    path_file_first_execution = first_response.json()["documentPath"]
    path_file_second_execution = second_response.json()["documentPath"]

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK
    assert path_file_first_execution == path_file_second_execution


@pytest.mark.asyncio
async def test_should_return200_and_merge_documents_and_add_watermark(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    payload = {
        "bucketName": main_bucket_name,
        "templatePaths": [
            "templates/template_1.docx",
            "templates/template_2.docx",
            "templates/google.pdf",
            "templates/form.pdf",
        ],
        "templateVariables": {
            "policy_number_al": 12345,
            "legal_name": "Friends",
            "dba_name": "LLC",
            "mailing_street": "90 Bedford St",
            "mailing_city": "New York",
            "mailing_state": "NY",
            "mailing_zip": "10014",
            "effective_date": "October 7, 2022 08:40:26 EST",
            "expiration_date": "October 7, 2023 08:40:26 EST",
            "tgl_rate": "650.10",
        },
        "watermarkPath": "templates/void_1.pdf",
    }

    response = await client.post("/api/v1/doc-generation/merge", json=payload)
    path_file = response.json()["documentPath"]
    obj_file = await storage_service.get_object(main_bucket_name, path_file)
    assert obj_file is not None
    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)

    assert response.status_code == status.HTTP_200_OK
    assert path_file.startswith("documents/") and path_file.endswith(".pdf")
    assert len(pdf_reader.pages) == 4
    for page in pdf_reader.pages[:2]:
        assert len(page.images)
