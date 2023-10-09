import functools
import hashlib
import uuid
from io import BytesIO
from pathlib import Path

import pypdftk

from app.config import settings


def build_tmp_full_path(sub_dir: Path, file_prefix: str) -> Path:
    return sub_dir / Path(f"{file_prefix}_{uuid.uuid4()}.pdf")


@functools.lru_cache()
def write_watermark(file_content: bytes):
    watermark_hash = hashlib.md5(file_content, usedforsecurity=False).hexdigest()

    watermark_path = settings.doc_gen.tmp_dir_path / Path(f"watermark_{watermark_hash}.pdf")
    if watermark_path.exists():
        return watermark_path

    with open(watermark_path, mode="wb") as tmp_file:
        tmp_file.write(file_content)

    return watermark_path


async def merge_pdf_documents(
    documents: list[tuple[BytesIO, Path | None]],
    sub_dir: Path
) -> BytesIO:
    document_paths: list[Path] = []
    for document, document_path in documents:
        if document_path is None:
            document_path = build_tmp_full_path(sub_dir, "document_with_watermark")  # noqa: WPS440

        with open(document_path, mode="wb") as document_tmp_file:
            document_tmp_file.write(document.read())
        document_paths.append(document_path)

    merged_path = build_tmp_full_path(sub_dir, "merged")
    pypdftk.concat(document_paths, merged_path)

    with open(merged_path, mode="rb") as merged_tmp_file:
        return BytesIO(merged_tmp_file.read())
