import asyncio
import logging
from io import BytesIO

from aiocache import Cache

from app.doc_generation.exception import (
    FileContentDoesntExistInRegistryException,
    FileDoesntExistException,
)
from app.doc_generation.models.template import ImageTemplateModel, TemplateModel
from app.doc_generation.schema import DocGenSingleRequest
from app.file_storage.service import FileStorageService


class FileRegistryService:
    storage_key_cache_timeout = 600  # 10 min * 60 sec

    def __init__(self, file_storage: FileStorageService):
        self.file_storage = file_storage

        self._cache = Cache(Cache.MEMORY)
        self._logger = logging.getLogger(self.__class__.__name__)

    async def register_template_model(self, request_model: DocGenSingleRequest) -> TemplateModel:
        bucket = request_model.bucket_name

        file_etag, header_etag, footer_etag, watermark_etag = await asyncio.gather(
            self._register_file(bucket, request_model.template_path),
            self._register_file(bucket, request_model.header_path),
            self._register_file(bucket, request_model.footer_path),
            self._register_file(bucket, request_model.watermark_path),
        )

        image_models = None
        if request_model.images:
            images_etags = await asyncio.gather(*[
                self._register_file(bucket, image_model.image_path)
                for image_model in request_model.images
            ])
            image_models = [
                ImageTemplateModel(
                    file_etag=etag,
                    width=image.width,
                    height=image.height,
                    variable_name=image.variable_name,
                )
                for etag, image in zip(images_etags, request_model.images)
            ]

        return TemplateModel(
            variables=request_model.template_variables,
            template_path=request_model.template_path,
            bucket=bucket,
            file_etag=file_etag,
            header_etag=header_etag,
            footer_etag=footer_etag,
            watermark_etag=watermark_etag,
            images=image_models
        )

    async def get_file_content(self, key: str) -> BytesIO:
        file_content = await self._cache.get(key)

        if file_content is None:
            raise FileContentDoesntExistInRegistryException()

        return BytesIO(file_content)

    async def _register_file(
        self,
        bucket: str,
        key: str | None = None,
    ) -> str | None:
        if key is None:
            return None

        file_metadata = await self.file_storage.get_object_metadata(bucket, key)
        if not file_metadata:
            raise FileDoesntExistException(key)

        etag = file_metadata["ETag"]
        if await self._cache.exists(etag):  # if file exists in cache we should update expire date
            await self._cache.expire(etag, self.storage_key_cache_timeout)
            return etag

        s3_obj = await self.file_storage.get_object(bucket, key)
        if not s3_obj:
            raise FileDoesntExistException(key)

        body = await s3_obj["Body"].read()
        await self._cache.set(etag, body, self.storage_key_cache_timeout)

        return etag
