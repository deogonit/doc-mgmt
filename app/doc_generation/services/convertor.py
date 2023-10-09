import asyncio
import logging
import os
import shutil
import time
from dataclasses import dataclass
from io import BytesIO
from operator import attrgetter
from pathlib import Path
from typing import Sequence, cast
from uuid import uuid4

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.doc_generation.enum import TemplateTypeEnum
from app.doc_generation.exception import (
    FolderAccessForbiddenException,
    UnsupportedTemplateExtensionException,
)
from app.doc_generation.models import (
    DocumentPutItem,
    DocumentSearchItem,
    TemplateModel,
    generate_hash_from_templates,
)
from app.doc_generation.processors import (
    AbstractDocumentProcessor,
    DocxDocumentProcessor,
    HtmlDocumentProcessor,
    PdfDocumentProcessor,
)
from app.doc_generation.processors.docx_template import ImageItem
from app.doc_generation.processors.pdf_utils import merge_pdf_documents
from app.doc_generation.repository import DocumentRepository
from app.doc_generation.schema import DocGenMergeRequest, DocGenMultipleItem, DocGenSingleRequest
from app.doc_generation.services.registry import FileRegistryService
from app.file_storage.service import FileStorageService


@dataclass
class DocGenMultipleResultItem:
    input_template_path: str
    document_path: str
    order_number: int
    document_content: BytesIO | None
    document_content_path: Path | None


class FileConvertorService:
    templates_path = Path("templates")
    documents_path = Path("documents")

    def __init__(
        self,
        api_client: GotenbergApiClient,
        file_storage: FileStorageService,
        file_registry: FileRegistryService,
        document_repository: DocumentRepository,
        main_bucket_name: str,
        app_version: str,
        expiration_date_in_seconds: int,
        tmp_dir_path: Path,
    ) -> None:
        self.api_client = api_client
        self.file_storage = file_storage
        self.file_registry = file_registry
        self.document_repository = document_repository
        self.main_bucket_name = main_bucket_name
        self.app_version = app_version
        self.expiration_date_in_seconds = expiration_date_in_seconds
        self.tmp_dir_path = tmp_dir_path

        self._logger = logging.getLogger(self.__class__.__name__)

    async def generate_documents(self, input_request: list[DocGenSingleRequest]) -> list[DocGenMultipleItem]:
        sub_dir = self._make_sub_dir()
        document_items = await self._generate_documents(input_request, sub_dir)

        shutil.rmtree(sub_dir)
        return [
            DocGenMultipleItem(
                input_template_path=doc_item.input_template_path,
                document_path=doc_item.document_path
            )
            for doc_item in document_items
        ]

    async def generate_documents_and_merge_it(self, input_request: list[DocGenSingleRequest]) -> str:
        sub_dir = self._make_sub_dir()
        document_items = await self._generate_documents(input_request, sub_dir)

        result_document = await merge_pdf_documents(
            [
                (doc_item.document_content, doc_item.document_content_path)
                for doc_item in document_items
                if doc_item.document_content
            ],
            sub_dir,
        )

        shutil.rmtree(sub_dir)
        return str(await self._save_document(result_document))

    async def generate_and_merge_documents(self, input_request: DocGenMergeRequest) -> str:
        sub_dir = self._make_sub_dir()
        template_models = await self._create_template_models(input_request.template_models)

        etags = [template_model.file_etag for template_model in template_models]
        hashed_image_models = None
        for template_model in template_models:
            if template_model.images:
                hashed_image_models = [
                    image_model.hashed_image_model
                    for image_model in template_model.images
                ]
                break

        hashed_templates = generate_hash_from_templates(
            etags,
            input_request.bucket_name,
            input_request.template_variables,
            template_models[0].watermark_etag if template_models else None,
            hashed_image_models,
        )

        founded_document_path = await self._get_result_file_path(etags, input_request.bucket_name, hashed_templates)
        if founded_document_path:
            return founded_document_path

        finished_processors = await self._create_processors(template_models, sub_dir)

        result_document = await merge_pdf_documents(
            [
                (processor.document_content, processor.document_content_path)
                for processor in finished_processors
            ],
            sub_dir,
        )

        document_path = str(await self._save_document(result_document))
        await self.document_repository.put_item(
            DocumentPutItem(
                etags=etags,
                bucket=input_request.bucket_name,
                hashed_request=hashed_templates,
                result_file=document_path,
                app_version=self.app_version,
                expiration_time=(int(time.time()) + int(self.expiration_date_in_seconds / 2)),
            )
        )

        shutil.rmtree(sub_dir)
        return document_path

    async def _generate_documents(
        self,
        input_request: list[DocGenSingleRequest],
        sub_dir: Path
    ) -> list[DocGenMultipleResultItem]:
        template_models = await self._create_template_models(input_request)

        for index_number, tmpl_model in enumerate(template_models):
            tmpl_model.order = index_number

        founded_document_paths = cast(
            list[str],
            await asyncio.gather(*[
                self._get_result_file_path(
                    [template_model.file_etag],
                    template_model.bucket,
                    template_model.hashed_template,
                )
                for template_model in template_models
            ])
        )

        document_items: list[DocGenMultipleResultItem] = []
        models_for_generating: list[TemplateModel] = []

        for template_index, document_path in enumerate(founded_document_paths):
            model = template_models[template_index]
            if document_path is None:
                models_for_generating.append(model)
                continue

            document_items.append(
                DocGenMultipleResultItem(
                    input_template_path=str(model.template_path),
                    document_path=str(document_path),
                    order_number=int(model.order),
                    document_content=None,
                    document_content_path=None,
                )
            )

        file_contents = await asyncio.gather(*[
            self.file_storage.download_file(self.main_bucket_name, doc_item.document_path)
            for doc_item in document_items
        ])
        for file_content, doc_item in zip(file_contents, document_items):
            doc_item.document_content = file_content

        if not models_for_generating:
            return document_items

        finished_processors = await self._create_processors(template_models, sub_dir)
        document_paths = await asyncio.gather(*[
            self._save_document(processor.document_content)
            for processor in finished_processors
        ])

        putting_item_tasks = []
        for template, doc_path, processor in zip(models_for_generating, document_paths, finished_processors):
            document_items.append(
                DocGenMultipleResultItem(
                    input_template_path=str(template.template_path),
                    document_path=str(doc_path),
                    order_number=int(template.order),
                    document_content=processor.document_content,
                    document_content_path=processor.document_content_path
                )
            )
            putting_item_tasks.append(
                self.document_repository.put_item(
                    DocumentPutItem(
                        etags=[template.file_etag],
                        bucket=template.bucket,
                        hashed_request=template.hashed_template,
                        result_file=str(doc_path),
                        app_version=self.app_version,
                        expiration_time=(int(time.time()) + int(self.expiration_date_in_seconds / 2)),
                    )
                )
            )
        await asyncio.gather(*putting_item_tasks)
        document_items.sort(key=attrgetter("order_number"))

        return document_items

    async def _create_template_models(self, input_request: list[DocGenSingleRequest]) -> list[TemplateModel]:
        for number_template, template in enumerate(input_request, start=1):
            self._logger.info(f"Template #{number_template} {template.json()}")

        register_models_tasks = [
            self.file_registry.register_template_model(single_request)
            for single_request in input_request
        ]
        template_models = await asyncio.gather(*register_models_tasks)
        return cast(list[TemplateModel], template_models)

    async def _create_processor(self, template_model: TemplateModel, sub_dir: Path) -> AbstractDocumentProcessor:
        is_relative_to_templates_folder = Path(template_model.template_path).is_relative_to(self.templates_path)
        if template_model.bucket == self.main_bucket_name and not is_relative_to_templates_folder:
            raise FolderAccessForbiddenException(template_model.template_path)

        template_file_content = await self.file_registry.get_file_content(template_model.file_etag)
        watermark_file_content = (
            await self.file_registry.get_file_content(template_model.watermark_etag)
            if template_model.watermark_etag else None
        )

        if template_model.template_path_suffix == TemplateTypeEnum.docx.value:
            images = await self._get_images(template_model)
            return DocxDocumentProcessor(
                api_client=self.api_client,
                sub_dir=sub_dir,
                template_file=template_file_content,
                template_path=template_model.template_path,
                template_variables=template_model.variables,
                watermark_file=watermark_file_content,
                images=images
            )
        elif template_model.template_path_suffix == TemplateTypeEnum.pdf.value:
            return PdfDocumentProcessor(
                api_client=self.api_client,
                sub_dir=sub_dir,
                template_file=template_file_content,
                template_path=template_model.template_path,
                template_variables=template_model.variables,
                watermark_file=watermark_file_content,
            )
        elif template_model.template_path_suffix == TemplateTypeEnum.html.value:
            file_contents = await self._get_headers_and_footers(template_model)

            return HtmlDocumentProcessor(
                api_client=self.api_client,
                sub_dir=sub_dir,
                template_file=template_file_content,
                template_path=template_model.template_path,
                template_variables=template_model.variables,
                watermark_file=watermark_file_content,
                header_file=file_contents["header_file"],
                footer_file=file_contents["footer_file"],
            )

        raise UnsupportedTemplateExtensionException(template_model.template_path_suffix)

    async def _get_headers_and_footers(self, template_model: TemplateModel) -> dict:
        if template_model.template_path_suffix != TemplateTypeEnum.html.value:
            return {}

        header_file_content = (
            await self.file_registry.get_file_content(template_model.header_etag)
            if template_model.header_etag else None
        )
        footer_file_content = (
            await self.file_registry.get_file_content(template_model.footer_etag)
            if template_model.footer_etag else None
        )
        return {
            "header_file": header_file_content,
            "footer_file": footer_file_content,
        }

    async def _get_images(self, template_model: TemplateModel) -> list[ImageItem] | None:
        if template_model.template_path_suffix != TemplateTypeEnum.docx.value or not template_model.images:
            return None

        file_contents = await asyncio.gather(*[
            self.file_registry.get_file_content(image_model.file_etag)
            for image_model in template_model.images
        ])

        return [
            ImageItem(
                file_etag=image_model.file_etag,
                width=image_model.width,
                height=image_model.height,
                variable_name=image_model.variable_name,
                file_content=file_content,
            )
            for file_content, image_model in zip(file_contents, template_model.images)
        ]

    async def _get_result_file_path(
        self,
        etags: list[str],
        bucket_name: str,
        hashed_request: str,
    ) -> str | None:
        document = await self.document_repository.search_item(
            DocumentSearchItem(
                etags=etags,
                bucket=bucket_name,
                hashed_request=hashed_request,
                app_version=self.app_version,
            )
        )

        if document and await self.file_storage.is_object_exists(document.bucket, document.result_file):
            return document.result_file

        return None

    async def _save_document(self, document: BytesIO) -> Path:
        random_name = str(uuid4())
        file_path = self.documents_path / f"{random_name}.pdf"
        await self.file_storage.upload_file(self.main_bucket_name, str(file_path), document)
        return file_path

    async def _create_processors(
        self,
        template_models: Sequence[TemplateModel],
        sub_dir: Path,
    ) -> list[AbstractDocumentProcessor]:
        create_processor_tasks = [
            self._create_processor(template_model, sub_dir)
            for template_model in template_models
        ]

        processors = cast(list[AbstractDocumentProcessor], await asyncio.gather(*create_processor_tasks))
        for processor in processors:
            processor.validate()

        document_tasks = [
            valid_processor.process_document()
            for valid_processor in processors
        ]
        finished_processors = await asyncio.gather(*document_tasks)
        return cast(list[AbstractDocumentProcessor], finished_processors)

    def _make_sub_dir(self) -> Path:
        sub_dir = self.tmp_dir_path / str(uuid4())
        os.mkdir(sub_dir)
        return sub_dir
