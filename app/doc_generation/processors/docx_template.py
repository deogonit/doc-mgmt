import copy
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.doc_generation.exception import (
    IncorrectProcessorState,
    InvalidTemplateException,
    MissingVariablesInTemplateException,
)
from app.doc_generation.processors.abstract_template import AbstractDocumentProcessor


@dataclass
class ImageItem:
    file_etag: str
    width: int
    height: int
    variable_name: str
    file_content: BytesIO


class DocxDocumentProcessor(AbstractDocumentProcessor):
    def __init__(
        self,
        api_client: GotenbergApiClient,
        sub_dir: Path,
        template_file: BytesIO,
        template_path: str,
        template_variables: dict[str, Any],
        watermark_file: BytesIO | None = None,
        images: list[ImageItem] | None = None,
    ):
        super().__init__(
            api_client=api_client,
            sub_dir=sub_dir,
            template_file=template_file,
            template_path=template_path,
            template_variables=template_variables,
            watermark_file=watermark_file
        )
        self.images = images

    def validate(self) -> None:
        doc = DocxTemplate(self.template_file)

        try:
            template_variables_from_doc = doc.get_undeclared_template_variables()
        except Exception:
            raise InvalidTemplateException(self.template_path)

        variables = set(self.template_variables.keys())
        if self.images:
            variables |= {image.variable_name for image in self.images}

        set_difference = set(template_variables_from_doc) - variables
        if set_difference:
            raise MissingVariablesInTemplateException(", ".join(set_difference), f"Template - {self.template_path}")

    async def render_document(self) -> bool:
        self._rendered_document = BytesIO()

        doc = DocxTemplate(self.template_file)
        variables = copy.deepcopy(self.template_variables)

        if self.images:
            images_variables = {
                image.variable_name: (
                    InlineImage(
                        doc,
                        image_descriptor=image.file_content,
                        width=Mm(image.width),
                        height=Mm(image.height),
                    )
                )
                for image in self.images
            }
            variables |= images_variables

        doc.render(variables, autoescape=True)
        doc.save(self._rendered_document)

        self._rendered_document.seek(0)

        return True

    async def convert_document(self) -> bool:
        if self._rendered_document is None:
            raise IncorrectProcessorState("_rendered_document")

        self._converted_document = await self.api_client.convert_docx_to_pdf(
            self._rendered_document,
            self.template_path,
        )

        return True
