from fastapi import status

from app.base.exception import BaseHTTPException


class DocumentConvertingException(BaseHTTPException):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    message = "Document converting failed. Timeout exceeded."

    is_expected = False
