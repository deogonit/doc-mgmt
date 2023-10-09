from fastapi import status

from app.base.exception import BaseHTTPException


class InvalidApiKeyException(BaseHTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Api key is invalid"
    field_name = "Authorization"

    is_ignored = True
    if_ignored = "InvalidApiKeyException occurred, traceback is not logged because of sensitive data"

    def __init__(self, api_key: str):
        super().__init__(field_value=api_key)
