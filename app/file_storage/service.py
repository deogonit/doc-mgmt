import logging
from io import BytesIO

from botocore.exceptions import ClientError
from types_aiobotocore_s3 import S3Client
from types_aiobotocore_s3.type_defs import (
    DeleteTypeDef,
    GetObjectOutputTypeDef,
    HeadObjectOutputTypeDef,
    ListObjectsV2OutputTypeDef,
    ObjectIdentifierTypeDef,
)

from app.file_storage.exception import DynamicS3Exception, NoSuchBucketException


class FileStorageService:  # noqa: WPS214
    storage_key_cache_timeout = 300  # 5 min * 60 sec

    def __init__(self, s3_client: S3Client):
        self._client = s3_client
        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_object(self, bucket: str, key: str) -> GetObjectOutputTypeDef | None:
        try:
            return await self._client.get_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "NoSuchKey":
                return None
            if exc.response["Error"]["Code"] == "NoSuchBucket":
                raise NoSuchBucketException(bucket)
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket, key=key)

    async def delete_object(self, bucket: str, key: str) -> None:
        await self._client.delete_object(Bucket=bucket, Key=key)

    async def download_file(self, bucket: str, key: str) -> BytesIO | None:
        try:
            s3_obj = await self.get_object(bucket, key)
        except ClientError as exc:
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket, key=key)

        if not s3_obj:
            return None

        body = await s3_obj["Body"].read()
        return BytesIO(body)

    async def upload_file(self, bucket: str, key: str, file_io: BytesIO) -> None:
        try:
            await self._client.upload_fileobj(Fileobj=file_io, Bucket=bucket, Key=key)
        except ClientError as exc:
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket, key=key)

    async def create_bucket(self, bucket: str) -> None:
        try:
            await self._client.create_bucket(Bucket=bucket)
        except ClientError as exc:
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket)

    async def clear_bucket(self, bucket: str) -> None:
        objects_response = await self.get_list_objects(bucket)

        file_objs = objects_response.get("Contents")
        if not file_objs:
            return

        keys: list[ObjectIdentifierTypeDef] = []
        for file_obj in file_objs:
            keys.append(ObjectIdentifierTypeDef(Key=file_obj["Key"]))

        try:
            await self._client.delete_objects(Bucket=bucket, Delete=DeleteTypeDef(Objects=keys, Quiet=True))
        except ClientError as del_exc:
            raise DynamicS3Exception(s3_exception=del_exc, bucket=bucket)

    async def delete_bucket(self, bucket: str) -> None:
        try:
            await self._client.delete_bucket(Bucket=bucket)
        except ClientError as exc:
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket)

    async def is_bucket_exists(self, bucket: str) -> bool:
        try:
            await self._client.head_bucket(Bucket=bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket)

        return True

    async def is_object_exists(self, bucket: str, key: str) -> bool:
        try:
            await self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"NoSuchKey", "404"}:
                return False
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket, key=key)

        return True

    async def get_object_metadata(self, bucket: str, key: str) -> HeadObjectOutputTypeDef | None:
        try:
            return await self._client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"NoSuchKey", "404"}:
                return None
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket, key=key)

    async def get_list_objects(self, bucket: str) -> ListObjectsV2OutputTypeDef:
        try:
            return await self._client.list_objects_v2(Bucket=bucket)
        except ClientError as exc:
            raise DynamicS3Exception(s3_exception=exc, bucket=bucket)
