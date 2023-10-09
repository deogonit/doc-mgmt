from io import BytesIO

from httpx import ConnectError, HTTPStatusError, Response
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_random,
)

from app.api_client.base_api_client import BaseApiClient, HTTPMethod
from app.api_client.exception import DocumentConvertingException
from app.base.exception import BaseHTTPException
from app.config import settings


class GotenbergApiClient(BaseApiClient):
    docx_content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    # for converting file from HTML to PDF file, your file must be named index.html
    # if you want to add header/footer in each page for your document, you should add header.html/footer.html files
    # https://gotenberg.dev/docs/modules/chromium#routes
    html_content_type = "text/html"
    html_header_file_name = "header.html"
    html_file_name = "index.html"
    html_footer_file_name = "footer.html"

    async def is_healthy(self) -> bool:
        endpoint = "/health"

        try:
            response = await self.client.request(
                url=self.base_url + endpoint,
                method=HTTPMethod.get.value,
            )
        except ConnectError:
            return False

        try:
            response.raise_for_status()
        except HTTPStatusError:
            return False

        return response.json().get("status") == "up"

    async def convert_docx_to_pdf(
        self,
        file_to_convert: BytesIO,
        template_path: str
    ) -> BytesIO:
        endpoint = "/forms/libreoffice/convert"

        response = await self._convert(
            endpoint=endpoint,
            files={"files": (template_path, file_to_convert.read(), self.docx_content_type)},
        )

        return BytesIO(response.content)

    async def convert_html_to_pdf(
        self,
        file_to_convert: BytesIO,
        header_file: BytesIO | None = None,
        footer_file: BytesIO | None = None,
    ) -> BytesIO:
        endpoint = "/forms/chromium/convert/html"
        files = {
            "main_file": (self.html_file_name, file_to_convert.read(), self.html_content_type)
        }

        if footer_file is not None:
            files["footer_file"] = (self.html_footer_file_name, footer_file.read(), self.html_content_type)

        if header_file is not None:
            files["header_file"] = (self.html_header_file_name, header_file.read(), self.html_content_type)

        response = await self._convert(
            endpoint=endpoint,
            files=files,
        )

        return BytesIO(response.content)

    @retry(
        reraise=True,
        wait=wait_random(min=settings.gotenberg.min_wait, max=settings.gotenberg.max_wait),
        stop=(stop_after_attempt(settings.gotenberg.max_attempt) | stop_after_delay(settings.gotenberg.max_timeout)),
        retry=retry_if_exception_type(BaseHTTPException),
    )
    async def _convert(self, endpoint: str, files: dict) -> Response:
        response = await self.client.request(
            url=self.base_url + endpoint,
            method=HTTPMethod.post.value,
            files=files,
            timeout=settings.gotenberg.max_timeout,
        )

        try:
            response.raise_for_status()
        except HTTPStatusError:  # noqa: WPS329
            raise DocumentConvertingException()

        return response
