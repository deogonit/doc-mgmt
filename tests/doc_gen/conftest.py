import pytest_asyncio

from app.container import Container
from app.doc_generation.services import FileRegistryService
from app.doc_generation.services.convertor import FileConvertorService
from app.file_storage.service import FileStorageService


@pytest_asyncio.fixture(scope="session")
async def storage_service(app_container: Container) -> FileStorageService:
    return await app_container.storage_service()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def convertor_service(app_container: Container) -> FileConvertorService:
    return await app_container.doc_gen_service()  # type: ignore


@pytest_asyncio.fixture(scope="session")
async def register_service(app_container: Container) -> FileRegistryService:
    return await app_container.registry_service()  # type: ignore
