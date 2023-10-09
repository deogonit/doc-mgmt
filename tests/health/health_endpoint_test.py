import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_should_return200_on_live_app(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "healthy"}
