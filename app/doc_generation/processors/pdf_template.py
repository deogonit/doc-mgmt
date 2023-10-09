import html

import pypdftk
from pypdf import PdfReader

from app.doc_generation.processors.abstract_template import AbstractDocumentProcessor


class PdfDocumentProcessor(AbstractDocumentProcessor):
    def validate(self) -> None:
        """
        Currently it's impossible to validate pdf forms properly,
        because existing forms have poor structure
        """

        return  # noqa: WPS324

    async def render_document(self) -> bool:
        reader = PdfReader(self.template_file)
        pdf_fields = reader.get_fields()
        self.template_file.seek(0)

        if not pdf_fields:
            return False

        self.patch_template_variables()

        form_path = self.build_tmp_full_path("form")
        self.write_file(form_path, self.template_file)

        escaped_variables = {
            tmpl_key: html.escape(tmpl_value) if isinstance(tmpl_value, str) else tmpl_value
            for tmpl_key, tmpl_value in self.template_variables.items()
        }

        rendered_document_path = self.build_tmp_full_path("rendered_document")
        pypdftk.fill_form(form_path, datas=escaped_variables, out_file=rendered_document_path, flatten=True)

        self._rendered_document_path = rendered_document_path

        return True

    async def convert_document(self) -> bool:
        return False

    def patch_template_variables(self):
        """
        This method is temporary fix for checkboxes
        https://github.com/CoverWhale/prime-doc-mgmt-k8s/issues/186
        Core app sends real checkbox value with `entity_type_` prefix (original field name) and `_x` suffix
        """

        for field_name, field_value in self.template_variables.items():
            if not field_name.endswith("_x"):
                continue
            origin_field_name = field_name[:-2]
            if origin_field_name not in self.template_variables:
                continue
            self.template_variables[origin_field_name] = field_value
