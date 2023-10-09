from io import BytesIO

import pytest
from fastapi import status
from httpx import AsyncClient
from pypdf import PdfReader

from app.file_storage.service import FileStorageService


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post("/api/v1/doc-generation/multiple/merge", json={}, headers={"Authorization": "rand"})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json() == {
        "detail": {
            "message": "Api key is invalid",
            "field": "Authorization",
            "value": "rand"
        }
    }


@pytest.mark.asyncio
async def test_should_return200_and_convert_docx_to_pdf(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    template_file_name1 = "templates/template_1.docx"
    template_variables1 = {
        "policy_number_al": 12345
    }

    template_file_name2 = "templates/template_2.docx"
    template_variables2 = {
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

    payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": str(template_file_name1),
                "templateVariables": template_variables1,
            },
            {
                "templatePath": str(template_file_name2),
                "templateVariables": template_variables2,
            }
        ]
    }
    response = await client.post("/api/v1/doc-generation/multiple/merge", json=payload)
    file_path = response.json()["documentPath"]
    obj_file = await storage_service.get_object(main_bucket_name, file_path)
    assert obj_file is not None
    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)

    assert response.status_code == status.HTTP_200_OK
    assert file_path.startswith("documents/")
    assert file_path.endswith(".pdf")
    assert len(pdf_reader.pages) == len(payload["templates"])


@pytest.mark.asyncio
async def test_should_return200_and_convert_docx_to_pdf_with_watermark(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    template_file_name1 = "templates/template_1.docx"
    template_variables1 = {
        "policy_number_al": 12345
    }

    template_file_name2 = "templates/template_2.docx"
    template_variables2 = {
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

    payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": str(template_file_name1),
                "templateVariables": template_variables1,
                "watermarkPath": "templates/void_1.pdf"
            },
            {
                "templatePath": str(template_file_name2),
                "templateVariables": template_variables2,
                "watermarkPath": "templates/void_1.pdf"
            }
        ]
    }
    response = await client.post("/api/v1/doc-generation/multiple/merge", json=payload)
    file_path = response.json()["documentPath"]
    obj_file = await storage_service.get_object(main_bucket_name, file_path)
    assert obj_file is not None
    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)

    assert response.status_code == status.HTTP_200_OK
    assert file_path.startswith("documents/") and file_path.endswith(".pdf")

    for page in pdf_reader.pages:
        assert len(page.images)


@pytest.mark.asyncio
async def test_should_return200_and_generate_documents_in_the_same_request(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    template_file_name1 = "templates/template_1.docx"
    template_variables1 = {
        "policy_number_al": 12345
    }

    template_file_name2 = "templates/template_2.docx"
    template_variables2 = {
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

    payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": str(template_file_name1),
                "templateVariables": template_variables1,
            },
            {
                "templatePath": str(template_file_name2),
                "templateVariables": template_variables2,
            }
        ]
    }
    first_response = await client.post("/api/v1/doc-generation/multiple/merge", json=payload)
    objects_after_first_response = await storage_service.get_list_objects(main_bucket_name)
    file_objects_after_first_response = objects_after_first_response.get("Contents")
    result_file_after_first_response = first_response.json()["documentPath"]

    second_response = await client.post("/api/v1/doc-generation/multiple/merge", json=payload)
    objects_after_second_response = await storage_service.get_list_objects(main_bucket_name)
    file_objects_after_second_response = objects_after_second_response.get("Contents")
    result_file_after_second_response = second_response.json()["documentPath"]

    assert (
        first_response.status_code == status.HTTP_200_OK
        and second_response.status_code == status.HTTP_200_OK
        and result_file_after_first_response != result_file_after_second_response
    )
    assert (
        file_objects_after_first_response is not None
        and file_objects_after_second_response is not None
    )

    file_names_after_first_response = [file_object["Key"] for file_object in file_objects_after_first_response]
    file_names_after_second_response = [file_object["Key"] for file_object in file_objects_after_second_response]

    # if client uses the endpoint /api/v1/doc-generation/multiple/merge,
    # server will return a new file.
    assert (len(file_names_after_first_response) + 1) == len(file_names_after_second_response)
    assert (
        result_file_after_first_response in file_names_after_second_response
        and result_file_after_second_response in file_names_after_second_response
    )
