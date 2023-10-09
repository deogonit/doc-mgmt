from unittest.mock import Mock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from starlette import status

SINGLE_ENDPOINT_URL = "/api/v1/doc-generation/single"


@pytest.mark.asyncio
async def test_should_return401_on_not_auth_header(client: AsyncClient):
    response = await client.post(SINGLE_ENDPOINT_URL, json={}, headers={"Authorization": "rand"})

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
        "templatePath": "sub_dir/doc.txt",
        "templateVariables": {},
    }

    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json() == {
        "detail": [
            {
                "message":
                    "Invalid template: sub_dir/doc.txt. "
                    + "Template path should have these ext: ['.docx', '.pdf', '.html']",
                "field": "templatePath",
                "type": "value_error"
            }
        ]
    }


@pytest.mark.asyncio
async def test_should_return404_with_non_exited_watermark_file(
    client: AsyncClient,
    main_bucket_name: str
):
    payload = {
        "bucketName": main_bucket_name,
        "templatePath": "templates/template_1.docx",
        "templateVariables": {
            "policy_number_al": 12345
        },
        "watermarkPath": "templates/void_x.pdf",
    }

    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "File by path does not exist",
            "value": "templates/void_x.pdf",
        }
    }


@pytest.mark.asyncio
async def test_should_return400_with_non_exited_ext(
    client: AsyncClient,
    mocker: MockerFixture,
    main_bucket_name: str
):
    mocker.patch("app.doc_generation.enum.TemplateTypeEnum.get_values", Mock(return_value=[".fake"]))

    payload = {
        "bucketName": main_bucket_name,
        "templatePath": "templates/file.fake",
        "templateVariables": {
            "policy_number_al": 12345
        }
    }
    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Unsupported template extension",
            "field": "templatePath",
            "value": ".fake"
        }
    }


@pytest.mark.asyncio
async def test_should_return404_with_non_exited_template_file(
    client: AsyncClient,
    main_bucket_name: str
):
    payload = {
        "bucketName": main_bucket_name,
        "templatePath": "templates/template_123.docx",
        "templateVariables": {
            "policy_number_al": 12345
        }
    }
    response = await client.post(SINGLE_ENDPOINT_URL, json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {
        "detail": {
            "message": "File by path does not exist",
            "value": "templates/template_123.docx",
        }
    }


@pytest.mark.asyncio
async def test_should_return403_on_folder_access_forbidden(client: AsyncClient, main_bucket_name: str):
    response = await client.post(
        SINGLE_ENDPOINT_URL,
        json={
            "bucketName": main_bucket_name,
            "templatePath": "templates_invalid/template_1.docx",
            "templateVariables": {
                "policy_number_al": 12345
            }
        }
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json() == {
        "detail": {
            "message": "Access to folder is forbidden",
            "field": "templatePath",
            "value": "templates_invalid/template_1.docx",
        }
    }


@pytest.mark.asyncio
async def test_should_return400_without_required_fields(
    client: AsyncClient,
    main_bucket_name: str
):
    response = await client.post(
        SINGLE_ENDPOINT_URL,
        json={
            "bucketName": main_bucket_name,
            "templatePath": "templates/template_1.docx",
            "templateVariables": {
                "first_policy_number_al": 12345
            }
        }
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "detail": {
            "message": "Not all required template variables were provided. Template - templates/template_1.docx",
            "field": "templateVariables",
            "value": "policy_number_al",
        }
    }
