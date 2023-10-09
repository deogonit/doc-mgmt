import pytest
from fastapi import status
from httpx import AsyncClient

from app.container import Container


@pytest.mark.asyncio
async def test_should_return200_on_ready_app(client: AsyncClient):
    response = await client.get("/ready")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "status": "healthy",
        "services": {
            "s3": "healthy",
            "dynamodb": "healthy",
            "docusign": "healthy",
            "gotenberg": "healthy",
        },
    }


@pytest.mark.asyncio
async def test_should_return400_and_misconfigured_on_misconfigured_service(
    client: AsyncClient,
    app_container: Container
):
    health_check_service = await app_container.health_check_service()  # type: ignore
    health_check_service._dynamodb_table_names = ["notExistingTable"]  # noqa: WPS437
    response = await client.get("/ready")
    app_container.health_check_service.reset()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "status": "misconfigured",
        "services": {
            "s3": "healthy",
            "dynamodb": "misconfigured",
            "docusign": "healthy",
            "gotenberg": "healthy",
        },
    }
