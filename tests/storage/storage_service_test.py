import json
from io import BytesIO
from typing import cast

import aiofiles
import pytest
from fastapi import status

from app.file_storage.exception import DynamicS3Exception, NoSuchBucketException
from app.file_storage.service import FileStorageService
from tests.constants import DATA_CONTAINER_PATH, GOOGLE_PDF

RANDOM_BUCKET_NAME = "random-bucket-name"


@pytest.mark.asyncio
async def test_should_create_check_delete_bucket(storage_service: FileStorageService):
    await storage_service.create_bucket(RANDOM_BUCKET_NAME)

    is_exists = await storage_service.is_bucket_exists(RANDOM_BUCKET_NAME)
    assert is_exists

    await storage_service.delete_bucket(RANDOM_BUCKET_NAME)


@pytest.mark.asyncio
async def test_should_return_none_when_object_not_exists(storage_service: FileStorageService, main_bucket_name: str):
    file_obj = await storage_service.get_object(main_bucket_name, "any-key.pdf")

    assert file_obj is None


@pytest.mark.asyncio
async def test_should_raise_exc_when_bucket_not_exists(storage_service: FileStorageService, main_bucket_name: str):
    try:
        await storage_service.get_object(RANDOM_BUCKET_NAME, "any-key.pdf")
    except NoSuchBucketException as exception:
        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert exception.message == "The specified bucket does not exist"
        assert exception.field_value == RANDOM_BUCKET_NAME
    else:
        raise AssertionError()


@pytest.mark.asyncio
async def test_should_upload_file(storage_service: FileStorageService, main_bucket_name: str):
    key = "test.pdf"
    async with aiofiles.open(DATA_CONTAINER_PATH / GOOGLE_PDF, mode="rb") as pdf_file:
        await storage_service.upload_file(main_bucket_name, key, cast(BytesIO, pdf_file))

    file_obj = await storage_service.get_object(main_bucket_name, key)

    assert file_obj is not None

    await storage_service.delete_object(main_bucket_name, key)


@pytest.mark.asyncio
async def test_should_download_file(storage_service: FileStorageService, main_bucket_name: str):
    key = "test.pdf"
    async with aiofiles.open(DATA_CONTAINER_PATH / GOOGLE_PDF, mode="rb") as pdf_file:
        await storage_service.upload_file(main_bucket_name, key, cast(BytesIO, pdf_file))

    file_io = await storage_service.download_file(main_bucket_name, key)

    assert file_io is not None

    head = file_io.read(10)
    assert head == b"%PDF-1.3\n%"

    await storage_service.delete_object(main_bucket_name, key)


@pytest.mark.asyncio
async def test_should_clear_delete_bucket(storage_service: FileStorageService):
    bucket_name = "new-test-bucket"

    await storage_service.create_bucket(bucket_name)

    key = "test.pdf"
    async with aiofiles.open(DATA_CONTAINER_PATH / GOOGLE_PDF, mode="rb") as pdf_file:
        await storage_service.upload_file(bucket_name, key, cast(BytesIO, pdf_file))

    await storage_service.clear_bucket(bucket_name)
    file_obj = await storage_service.get_object(bucket_name, key)
    assert file_obj is None

    await storage_service.delete_bucket(bucket_name)


@pytest.mark.asyncio
async def test_should_raise_exc_when_try_to_delete_non_existing_bucket(storage_service: FileStorageService):
    bucket_name = "non-existing-bucket"

    try:
        await storage_service.delete_bucket(bucket_name)
    except DynamicS3Exception as exception:
        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert json.loads(exception.message) == {
            "Code": "NoSuchBucket",
            "Message": "The specified bucket does not exist",
            "BucketName": "non-existing-bucket",
            "Resource": "/non-existing-bucket",
        }
        assert exception.field_value == "non-existing-bucket"
    else:
        raise AssertionError()
