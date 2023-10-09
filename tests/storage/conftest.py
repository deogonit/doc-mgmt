import pytest_asyncio

from app.container import Container
from app.file_storage.service import FileStorageService


@pytest_asyncio.fixture(scope="session")
async def storage_service(app_container: Container) -> FileStorageService:
    return await app_container.storage_service()  # type: ignore
