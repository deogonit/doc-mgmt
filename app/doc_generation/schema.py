from pathlib import Path

from pydantic import Field, validator

from app.base.schema import ApiBaseModel
from app.config import settings
from app.doc_generation.enum import TemplateTypeEnum

bucket_name_field = Field(
    default=settings.storage.main_bucket_name,
    description="S3 bucket name with templates",
)


class ImageItemRequest(ApiBaseModel):
    variable_name: str
    image_path: str
    width: int
    height: int


class DocGenSingleRequest(ApiBaseModel):
    bucket_name: str = bucket_name_field
    template_path: str
    template_variables: dict

    watermark_path: str | None
    header_path: str | None = None
    footer_path: str | None = None
    images: list[ImageItemRequest] | None = None

    @validator("template_path")
    def template_path_should_contain_correct_ext(cls, template_path_value: str):
        file_extensions = TemplateTypeEnum.get_values()

        if Path(template_path_value).suffix not in file_extensions:
            raise ValueError(
                f"Invalid template: {template_path_value}. Template path should have these ext: {file_extensions}"
            )

        return template_path_value


class DocGenMergeRequest(ApiBaseModel):
    bucket_name: str = bucket_name_field
    template_paths: list[str]
    template_variables: dict

    images: list[ImageItemRequest] | None = None
    watermark_path: str | None

    @validator("template_paths")
    def template_paths_should_contain_correct_ext(cls, template_paths: list[str]):
        if not template_paths:
            raise ValueError("templatePaths value can't be empty")

        file_extensions = TemplateTypeEnum.get_values()

        invalid_templates = []
        for template_path in template_paths:
            if Path(template_path).suffix not in file_extensions:
                invalid_templates.append(template_path)

        if invalid_templates:
            raise ValueError(
                f"Invalid templates: {invalid_templates}. Template path should have these ext: {file_extensions}"
            )

        return template_paths

    @property
    def template_models(self) -> list[DocGenSingleRequest]:
        template_models: list[DocGenSingleRequest] = []

        for template_path in self.template_paths:
            images = None
            if Path(template_path).suffix == TemplateTypeEnum.docx.value:
                images = self.images

            template_models.append(
                DocGenSingleRequest(
                    template_path=template_path,
                    template_variables=self.template_variables,
                    watermark_path=self.watermark_path,
                    header_path=None,
                    footer_path=None,
                    bucket_name=self.bucket_name,
                    images=images,
                )
            )

        return template_models


class DocGenMultipleRequest(ApiBaseModel):
    templates: list[DocGenSingleRequest]

    @validator("templates")
    def template_path_should_contain_correct_ext(cls, templates: list[DocGenSingleRequest]):
        if not templates:
            raise ValueError("templates value can't be empty")
        return templates


class DocGenSingleResponse(ApiBaseModel):
    bucket_name: str = bucket_name_field
    document_path: str


class DocGenMultipleItem(ApiBaseModel):
    input_template_path: str
    document_path: str


class DocGenMultipleResponse(ApiBaseModel):
    bucket_name: str = bucket_name_field
    documents: list[DocGenMultipleItem]
