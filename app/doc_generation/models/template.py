import hashlib
import json
from pathlib import Path

from pydantic import PrivateAttr

from app.base.models import DBBaseModel


def _generate_hash(object_to_encode: dict) -> str:
    encoded_object = json.dumps(object_to_encode, sort_keys=True).encode("utf-8")
    return hashlib.md5(encoded_object, usedforsecurity=False).hexdigest()


def generate_hash_from_templates(
    etags: list[str],
    bucket: str,
    variables: dict,
    watermark_etag: str | None = None,
    images_etags: list[str] | None = None
) -> str:
    object_to_encode = {
        "etags": etags,
        "variables": variables,
        "bucket": bucket,
        "watermark_etag": watermark_etag,
        "images": images_etags
    }
    return _generate_hash(object_to_encode)


class ImageTemplateModel(DBBaseModel):
    file_etag: str
    width: int
    height: int
    variable_name: str

    @property
    def hashed_image_model(self) -> str:
        object_to_encode = self.dict()
        return _generate_hash(object_to_encode)


class TemplateModel(DBBaseModel):
    file_etag: str
    variables: dict
    bucket: str
    template_path: str
    order: int = -1

    header_etag: str | None = None
    footer_etag: str | None = None
    watermark_etag: str | None = None
    images: list[ImageTemplateModel] | None = None

    _template_path_suffix: str | None = PrivateAttr(default=None)

    @property
    def hashed_template(self) -> str:
        object_to_encode = self.dict()
        return _generate_hash(object_to_encode)

    @property
    def template_path_suffix(self) -> str:
        if self._template_path_suffix is not None:
            return self._template_path_suffix

        self._template_path_suffix = Path(self.template_path).suffix   # noqa: WPS601
        return self._template_path_suffix
