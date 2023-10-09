import time
from io import BytesIO

import pytest
from httpx import AsyncClient
from pypdf import PdfReader
from starlette import status

from app.container import Container
from app.doc_generation.services import FileRegistryService
from app.file_storage.service import FileStorageService
from tests.constants import SIGNATURE_IMAGE, TEMPLATE4_DOCX

SINGLE_ENDPOINT_URL = "/api/v1/doc-generation/single"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "primary_payload, expected_value_in_first_page",
    [
        # Case 1: docx to pdf
        (
            {
                "templatePath": "templates/template_1.docx",
                "templateVariables": {
                    "policy_number_al": 12345
                },
            },
            "12345"
        ),
        # Case 2: html to pdf
        (
            {
                "templatePath": "templates/invoice.html",
                "templateVariables": {
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
            },
            "000000135176"
        ),
        # Case 3: pdf form to pdf
        (
            {
                "templatePath": "templates/form.pdf",
                "templateVariables": {
                    "tgl_rate": "650.10",
                    "entity_type_individual": "individual",
                    "entity_type_individual_x": "X",
                }
            },
            ""
        ),
        # Case 4: docx document with images
        (
            {
                "templatePath": f"templates/{TEMPLATE4_DOCX}",
                "templateVariables": {
                    "carrier_al_name": "Company NAME",
                    "producer_name": "Producer NAME",
                    "legal_name": "Named Insured",
                    "mailing_street": "Mailing Address",
                    "mailing_city": "Florida",
                    "mailing_state": "FL",
                    "mailing_zip": "32003",
                    "effective_date_transaction": "September 27, 2023",
                    "expiration_date_transaction": "September 27, 2024",
                    "entity_type": "Form Of Business",
                    "total_premium_endorsements_al_total": "$13,961.41",
                    "form_title": "Form Title",
                    "form_number": "Form Number",
                    "form_edition": "Form Edition",
                    "signature_name": "Signature Name",
                    "signature_title": "Signature Title",
                    "effective_date": "September 27, 2023"
                },
                "images": [
                    {
                        "variable_name": "signature_img",
                        "image_path": f"images/{SIGNATURE_IMAGE}",
                        "width": 100,
                        "height": 50
                    }
                ],
            },
            ""
        ),
        # Case 5: fpdf form with special `<` and `>` characters
        (
            {
                "templatePath": "templates/acord_25.pdf",
                "templateVariables": {
                    "agent_email": "Scooter Howard <Scooter@example.com>"
                },
            },
            "Scooter Howard <Scooter@example.com>"
        ),
    ],
)
async def test_should_return200_and_convert_file_to_pdf(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
    primary_payload,
    expected_value_in_first_page: str,
):
    payload = primary_payload | {"mainBucketName": main_bucket_name}
    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)
    file_path = response.json()["documentPath"]
    obj_file = await storage_service.get_object(response.json()["bucketName"], file_path)
    assert obj_file is not None

    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)
    text_from_first_page = pdf_reader.pages[0].extract_text()

    assert response.status_code == status.HTTP_200_OK
    assert file_path.startswith("documents/") and file_path.endswith(".pdf")
    assert expected_value_in_first_page in text_from_first_page


@pytest.mark.asyncio
async def test_should_return200_and_convert_file_and_register_template_in_cache(
    client: AsyncClient,
    storage_service: FileStorageService,
    register_service: FileRegistryService,
    main_bucket_name: str,
):
    template_path_file = "templates/template_1.docx"
    payload = {
        "bucketName": main_bucket_name,
        "templatePath": template_path_file,
        "templateVariables": {
            "policy_number_al": 12345
        },
    }

    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)
    template_metadata = await storage_service.get_object_metadata(main_bucket_name, template_path_file)

    assert template_metadata is not None

    etag_template_file = template_metadata["ETag"]
    template_file_content = await register_service.get_file_content(etag_template_file)

    assert response.status_code == status.HTTP_200_OK
    assert template_file_content is not None
    assert template_file_content.getbuffer().nbytes > 0


@pytest.mark.asyncio
async def test_should_return200_convert_html_file_to_pdf_with_footer(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str,
):
    payload = {
        "bucketName": main_bucket_name,
        "templatePath": "templates/invoice.html",
        "footerPath": "templates/footer.html",
        "templateVariables": {
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
    }

    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)
    file_path = response.json()["documentPath"]
    obj_file = await storage_service.get_object(response.json()["bucketName"], file_path)
    assert obj_file is not None

    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)
    text_from_first_page = pdf_reader.pages[0].extract_text()

    assert response.status_code == status.HTTP_200_OK
    assert file_path.startswith("documents/") and file_path.endswith(".pdf")
    assert "Cover Whale Insurance Solutions" in text_from_first_page and "1 of 2" in text_from_first_page


@pytest.mark.asyncio
async def test_should_return200_convert_and_add_watermark(
    client: AsyncClient,
    storage_service: FileStorageService,
    main_bucket_name: str
):
    response = await client.post(
        SINGLE_ENDPOINT_URL,
        json={
            "bucketName": main_bucket_name,
            "templatePath": "templates/template_1.docx",
            "templateVariables": {
                "policy_number_al": 12345
            },
            "watermarkPath": "templates/void_1.pdf",
        }
    )
    path_file = response.json()["documentPath"]
    obj_file = await storage_service.get_object(main_bucket_name, path_file)
    assert obj_file is not None

    pdf_file = BytesIO(await obj_file["Body"].read())
    pdf_reader = PdfReader(pdf_file)

    assert response.status_code == status.HTTP_200_OK
    assert path_file.startswith("documents/") and path_file.endswith(".pdf")
    assert len(pdf_reader.pages[0].images) == 1


@pytest.mark.asyncio
async def test_should_return200_convert_but_with_diff_app_version(
    client: AsyncClient,
    app_container: Container,
    main_bucket_name: str
):
    convertor_service = await app_container.doc_gen_service()  # type: ignore
    data_payload = {
        "bucketName": main_bucket_name,
        "templatePath": "templates/template_1.docx",
        "templateVariables": {
            "policy_number_al": int(time.time())
        }
    }

    first_response = await client.post(
        SINGLE_ENDPOINT_URL,
        json=data_payload
    )
    convertor_service.app_version = "different"
    second_response = await client.post(
        SINGLE_ENDPOINT_URL,
        json=data_payload
    )
    app_container.doc_gen_service.reset()

    path_file_from_first_response = first_response.json()["documentPath"]
    path_file_from_second_response = second_response.json()["documentPath"]

    assert first_response.status_code == status.HTTP_200_OK and second_response.status_code == status.HTTP_200_OK
    assert (
        path_file_from_first_response.startswith("documents/")
        and path_file_from_second_response.startswith("documents/")
    )
    assert path_file_from_first_response != path_file_from_second_response
