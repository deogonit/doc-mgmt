from io import BytesIO

import pytest
from fastapi import status
from httpx import AsyncClient
from pypdf import PdfReader

from app.file_storage.service import FileStorageService


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post("/api/v1/doc-generation/multiple", json={}, headers={"Authorization": "rand"})

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
        "templates": [
            {
                "templatePath": "sub_dir/file.txt",
                "templateVariables": {},
            }
        ]
    }

    response = await client.post("/api/v1/doc-generation/multiple", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {
        "detail": [
            {
                "message":
                    "Invalid template: sub_dir/file.txt. "
                    + "Template path should have these ext: ['.docx', '.pdf', '.html']",
                "field": "templates.0.templatePath",
                "type": "value_error"
            }
        ]
    }


@pytest.mark.asyncio
async def test_should_return200_and_convert_docx_to_pdf(
    client: AsyncClient,
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
    response = await client.post("/api/v1/doc-generation/multiple", json=payload)
    response_template_paths = [doc["inputTemplatePath"] for doc in response.json()["documents"]]

    assert response.status_code == status.HTTP_200_OK
    assert response_template_paths == [str(template_file_name1), str(template_file_name2)]


@pytest.mark.asyncio
async def test_should_return200_and_convert_only_one_document(
    client: AsyncClient,
    main_bucket_name: str
):
    template_file_name1 = "templates/invoice.html"
    template_variables1 = {
        "invoice_name": "CW-000000135176",
        "al_policy_name": "CW1EIC-990112-00",
        "apd_policy_name": "CW2971337-00",
        "mtc_policy_name": "CW2265226-00",
        "tgl_policy_name": "CUS02488957-00",
        "ntl_policy_name": "TPM2726204-00",
        "trucking_invoice_name": "aa",
        "insured_name": "aa (DBA: aaa)",
        "short_address_name": "aaa",
        "full_address_name": "aaa, FL 32003",
        "from_date_time": "September 27, 2022 15:00:48 EST(Eastern Standard Time)",
        "to_date_time": "September 27, 2023",
        "full_broker_contact": "M.J. Hall and Company - firstname_135 lastname_135 (minaiti2011@gmail.com)",
        "total_premium": "$13,961.41",
        "uninsured_damage": "$134.67",
        "injury_protection": "$270.78",
        "policy_fees": "$0.00",
        "underwriting_fees": "$0.00",
        "lines_taxes": "$0.00",
        "stamping_fees": "$0.00",
        "policy_cost": "$14,366.86",
        "al_commission": "-$2,011.36",
        "surplus_lines_taxes": "-$0.00",
        "net_due_to": "$12,355.50",
        "due_by_cost": "CW-000000135176",
        "due_by_date": "October 27, 2022",
        "check_payable_to": "Cover Whale Insurance Solutions Inc. - Premium Trust",
        "mailing_address": "PO Box 116, Farmington, CT 06034-0116",
        "insured_account": "2250731",
        "email_to_questions": "billing@coverwhale.com"
    }

    template_file_name2 = "templates/template_1.docx"
    template_variables2 = {
        "policy_number_al": 1234567890
    }

    template_file_name3 = "templates/template_1.docx"
    template_variables3 = {
        "policy_number_al": 12345
    }

    first_payload = {
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
    second_payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": str(template_file_name1),
                "templateVariables": template_variables1,
            },
            {
                "templatePath": str(template_file_name3),
                "templateVariables": template_variables3,
            }
        ]
    }

    first_response = await client.post("/api/v1/doc-generation/multiple", json=first_payload)
    second_response = await client.post("/api/v1/doc-generation/multiple", json=second_payload)
    first_item_from_first_resp, second_item_from_first_resp = first_response.json()["documents"]
    first_item_from_second_resp, second_item_from_second_resp = second_response.json()["documents"]

    assert first_response.status_code == status.HTTP_200_OK
    assert second_response.status_code == status.HTTP_200_OK
    assert first_item_from_first_resp["documentPath"] == first_item_from_second_resp["documentPath"]
    assert second_item_from_first_resp["documentPath"] != second_item_from_second_resp["documentPath"]


@pytest.mark.asyncio
async def test_should_return200_convert_two_files_and_add_watermarks(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": "templates/template_1.docx",
                "templateVariables": {
                    "policy_number_al": 12345
                },
                "watermarkPath": "templates/void_1.pdf",
            },
            {
                "templatePath": "templates/template_1.docx",
                "templateVariables": {
                    "policy_number_al": 12345
                },
                "watermarkPath": "templates/void_2.pdf",
            }
        ]
    }
    response = await client.post("/api/v1/doc-generation/multiple", json=payload)
    doc_items = response.json()["documents"]

    assert response.status_code == status.HTTP_200_OK
    assert len(doc_items) == 2
    for doc_item in doc_items:
        path = doc_item["documentPath"]
        obj_file = await storage_service.get_object(main_bucket_name, path)
        assert obj_file is not None

        pdf_file = BytesIO(await obj_file["Body"].read())
        pdf_reader = PdfReader(pdf_file)

        assert path.startswith("documents/") and path.endswith(".pdf")
        assert len(pdf_reader.pages[0].images) == 1


@pytest.mark.asyncio
async def test_should_return200_and_convert_two_files_and_add_watermark(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    payload = {
        "bucketName": main_bucket_name,
        "templates": [
            {
                "templatePath": "templates/template_1.docx",
                "templateVariables": {
                    "policy_number_al": 12345
                },
            },
            {
                "templatePath": "templates/template_1.docx",
                "templateVariables": {
                    "policy_number_al": 12345
                },
                "watermarkPath": "templates/void_2.pdf",
            }
        ]
    }
    response = await client.post("/api/v1/doc-generation/multiple", json=payload)
    doc_items = response.json()["documents"]

    assert response.status_code == status.HTTP_200_OK
    assert len(doc_items) == 2
    for doc_item in doc_items:
        path = doc_item["documentPath"]
        obj_file = await storage_service.get_object(main_bucket_name, path)

        assert obj_file is not None
        assert path.startswith("documents/")
        assert path.endswith(".pdf")
