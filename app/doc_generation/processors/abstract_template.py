import logging
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import Any

import pypdftk
from typing_extensions import Self

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.doc_generation.exception import IncorrectProcessorState
from app.doc_generation.processors.pdf_utils import build_tmp_full_path, write_watermark


class AbstractDocumentProcessor(ABC):
    def __init__(
        self,
        api_client: GotenbergApiClient,
        sub_dir: Path,
        template_file: BytesIO,
        template_path: str,
        template_variables: dict[str, Any],
        watermark_file: BytesIO | None,
    ):
        self.api_client: GotenbergApiClient = api_client
        self.sub_dir: Path = sub_dir

        self.template_file: BytesIO = template_file
        self.template_path: str = template_path
        self.template_variables: dict[str, Any] = template_variables

        self.watermark_file: BytesIO | None = watermark_file

        self._rendered_document: BytesIO | None = None
        self._rendered_document_path: Path | None = None

        self._converted_document: BytesIO | None = None
        self._converted_document_path: Path | None = None

        self._document_with_watermark: BytesIO | None = None
        self._document_with_watermark_path: Path | None = None

        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)

    @property
    def document_content(self) -> BytesIO:
        if self._document_with_watermark is None:
            raise IncorrectProcessorState("_document_with_watermark")

        document_content = BytesIO(self._document_with_watermark.read())
        self._document_with_watermark.seek(0)

        return document_content

    @property
    def document_content_path(self) -> Path | None:
        if self._document_with_watermark_path is None:
            return None

        return self._document_with_watermark_path

    @abstractmethod
    def validate(self) -> None:
        """Validate template"""

    async def process_document(self) -> Self:
        """
        Document process is split in 3 pieces:
        1. Render - inject template's values in templates/form
        2. Convert - convert html/docx into pdf
        3. Apply watermark - if there's watermark in request - it'll be applied.

        If concrete processor doesn't have logic for specific stape - it can skip it by returning False value
        and document content and/or document local path will be copied from previous step.
        """
        render_done = await self.render_document()
        if not render_done:
            self.skip_render_document()

        convert_done = await self.convert_document()
        if not convert_done:
            self.skip_convert_document()

        watermark_done = await self.apply_watermark()
        if not watermark_done:
            self.skip_apply_watermark()

        return self

    @abstractmethod
    async def render_document(self) -> bool:
        """Render document based on template"""

    def skip_render_document(self) -> None:
        """Skip document render"""

        self._rendered_document_path = None
        self._rendered_document = BytesIO(self.template_file.read())

    @abstractmethod
    async def convert_document(self) -> bool:
        """Convert document to pdf format"""

    def skip_convert_document(self) -> None:
        """Skip document render"""

        self._converted_document_path = self._rendered_document_path

        if self._rendered_document:
            self._converted_document = BytesIO(self._rendered_document.read())

    async def apply_watermark(self) -> bool:
        if self.watermark_file is None:
            return False

        if self._converted_document_path is None:
            self._converted_document_path = self.build_tmp_full_path("converted_document")
            self.write_file(self._converted_document_path, self._converted_document)  # type: ignore

        watermark_content = self.watermark_file.read()
        watermark_path = write_watermark(watermark_content)

        await self.apply_watermark_by_path(self._converted_document_path, watermark_path)

        return True

    def skip_apply_watermark(self) -> None:
        """Skip watermark apply"""

        self._document_with_watermark_path = self._converted_document_path
        if self._converted_document:
            self._document_with_watermark = BytesIO(self._converted_document.read())
        elif self._document_with_watermark_path:
            self._document_with_watermark = self.read_file(self._document_with_watermark_path)
        else:
            raise IncorrectProcessorState("_document_with_watermark/_document_with_watermark_path")

    async def apply_watermark_by_path(self, document_path: Path, watermark_path: Path) -> None:
        document_with_watermark_path = self.build_tmp_full_path("document_with_watermark")
        pypdftk.stamp(document_path, watermark_path, document_with_watermark_path)

        self._document_with_watermark_path = document_with_watermark_path
        self._document_with_watermark = self.read_file(document_with_watermark_path)

    def build_tmp_full_path(self, file_prefix: str) -> Path:
        return build_tmp_full_path(self.sub_dir, file_prefix)

    @classmethod
    def write_file(cls, file_path: Path, file_content: BytesIO) -> None:
        with open(file_path, mode="wb") as tmp_file:
            tmp_file.write(file_content.read())
            file_content.seek(0)

    @classmethod
    def read_file(cls, file_path: Path) -> BytesIO:
        with open(file_path, mode="rb") as tmp_file:
            return BytesIO(tmp_file.read())
