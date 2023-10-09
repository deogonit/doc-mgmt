from io import BytesIO
from pathlib import Path
from typing import Any

from jinja2 import Environment, Template, meta, select_autoescape

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.doc_generation.exception import (
    IncorrectProcessorState,
    InvalidTemplateException,
    MissingVariablesInTemplateException,
)
from app.doc_generation.processors.abstract_template import AbstractDocumentProcessor


class HtmlDocumentProcessor(AbstractDocumentProcessor):
    def __init__(
        self,
        api_client: GotenbergApiClient,
        sub_dir: Path,
        template_file: BytesIO,
        template_path: str,
        template_variables: dict[str, Any],
        watermark_file: BytesIO | None = None,
        header_file: BytesIO | None = None,
        footer_file: BytesIO | None = None,
    ):
        super().__init__(
            api_client=api_client,
            sub_dir=sub_dir,
            template_file=template_file,
            template_path=template_path,
            template_variables=template_variables,
            watermark_file=watermark_file
        )
        self.header_file = header_file
        self.footer_file = footer_file
        self._environment = Environment(autoescape=select_autoescape(["html"]))

    def validate(self) -> None:
        file_content = str(self.template_file.getvalue())
        parsed_content = self._environment.parse(file_content)
        try:
            template_variables = meta.find_undeclared_variables(parsed_content)
        except Exception:
            raise InvalidTemplateException(self.template_path)

        set_difference = set(template_variables) - set(self.template_variables.keys())
        if set_difference:
            raise MissingVariablesInTemplateException(", ".join(set_difference))

    async def render_document(self) -> bool:
        template = Template(self.template_file.getvalue().decode("utf-8"))
        output = template.render(**self.template_variables)

        self._rendered_document = BytesIO(bytes(output, "utf-8"))

        return True

    async def convert_document(self) -> bool:
        if self._rendered_document is None:
            raise IncorrectProcessorState("_rendered_document")

        self._converted_document = await self.api_client.convert_html_to_pdf(
            self._rendered_document,
            self.header_file,
            self.footer_file,
        )

        return True
