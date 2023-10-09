import asyncio
import os
import shutil
from io import BytesIO
from typing import AsyncGenerator, cast

import aiofiles
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient

from app.container import Container
from app.main import create_app
from tests.constants import (
    DATA_CONTAINER_PATH,
    LIST_FILES_TO_UPLOAD,
    SIGNATURE_IMAGE,
    TEMPLATE1_DOCX,
)


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    loop.close()


@pytest.fixture(scope="session")
def app():
    yield create_app()


@pytest.fixture(scope="session")
def app_container(app: FastAPI) -> Container:
    return app.container  # type: ignore


@pytest.fixture(scope="session")
def global_settings(app_container: Container) -> dict:
    return app_container.config()


@pytest.fixture(scope="session")
def main_bucket_name(global_settings: dict) -> str:
    return global_settings["storage"]["main_bucket_name"]


@pytest_asyncio.fixture(scope="session")
async def s3_storage(app_container: Container, main_bucket_name: str) -> AsyncGenerator[None, None]:
    storage_service = await app_container.storage_service()  # type: ignore
    is_exists = await storage_service.is_bucket_exists(main_bucket_name)

    if not is_exists:
        await storage_service.create_bucket(main_bucket_name)

    for name_file in LIST_FILES_TO_UPLOAD:
        async with aiofiles.open(DATA_CONTAINER_PATH / name_file, mode="rb") as file_to_upload:
            await storage_service.upload_file(main_bucket_name, f"templates/{name_file}", cast(BytesIO, file_to_upload))

    async with aiofiles.open(DATA_CONTAINER_PATH / TEMPLATE1_DOCX, mode="rb") as invalid_template:
        await storage_service.upload_file(
            main_bucket_name, f"templates_invalid/{TEMPLATE1_DOCX}", cast(BytesIO, invalid_template)
        )

    async with aiofiles.open(DATA_CONTAINER_PATH / SIGNATURE_IMAGE, mode="rb") as image_file:
        await storage_service.upload_file(
            main_bucket_name, f"images/{SIGNATURE_IMAGE}", cast(BytesIO, image_file)
        )

    yield

    await storage_service.clear_bucket(main_bucket_name)
    await storage_service.delete_bucket(main_bucket_name)


@pytest_asyncio.fixture(scope="session")
async def dynamo_database(app: FastAPI, global_settings: dict) -> AsyncGenerator[None, None]:
    dynamodb_client = await app.container.dynamodb_client()  # type: ignore
    tables_and_pk_names = [
        (global_settings["dynamo_storage"]["documents_table_name"], "id"),
        (global_settings["dynamo_storage"]["envelopes_table_name"], "envelope_id"),
        (global_settings["dynamo_storage"]["envelope_callbacks_table_name"], "envelope_id"),
    ]

    for table_name_for_create, primary_key_name in tables_and_pk_names:
        create_table_input_request = {
            "TableName": table_name_for_create,
            "KeySchema": [
                {"AttributeName": primary_key_name, "KeyType": "HASH"}
            ],
            "AttributeDefinitions": [
                {"AttributeName": primary_key_name, "AttributeType": "S"}
            ],
            "ProvisionedThroughput": {
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10
            }
        }
        await dynamodb_client.create_table(**create_table_input_request)

    yield

    for table_for_delete in tables_and_pk_names:
        table_name = table_for_delete[0]
        await dynamodb_client.delete_table(TableName=table_name)


@pytest_asyncio.fixture(scope="session")
async def file_storage(global_settings: dict) -> AsyncGenerator[None, None]:
    dir_name = global_settings["doc_gen"]["tmp_dir_path"]
    os.mkdir(dir_name)

    yield

    shutil.rmtree(dir_name)


@pytest_asyncio.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with LifespanManager(app):
        async with AsyncClient(
            app=app,
            base_url="http://testserver",
            headers={
                "Content-Type": "application/json",
                "Authorization": "xxx",
            }
        ) as server_client:
            yield server_client


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_app(
    client: AsyncGenerator[AsyncClient, None],
    s3_storage: AsyncGenerator[None, None],
    dynamo_database: AsyncGenerator[None, None],
    file_storage: AsyncGenerator[None, None],
):
    """Autouse fixture to init and destroy services and create resources in proper order"""
