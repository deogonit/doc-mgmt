import json
from http import HTTPStatus

import docusign_esign
from fastapi import status

from app.base.exception import BaseHTTPException
from app.esign.enum import ExcErrorCodeEnum, ExcErrorMessageEnum


class EnvelopeInDbDoesntExistException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Envelop by id does not exist in database"
    field_name = "envelopeId"

    def __init__(self, envelope_id: str):
        super().__init__(field_value=envelope_id)


class EnvelopeInCreatingStatusException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Actions with the document in the custom:creating status are prohibited"
    field_name = "envelopeId"

    def __init__(self, envelope_id: str):
        super().__init__(field_value=envelope_id)


class DocumentDoesntExistException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Document by path does not exist"
    field_name = "documentPath"

    def __init__(self, document_path: str):
        super().__init__(field_value=document_path)


class InvalidAuthenticationCreds(BaseHTTPException):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid bearer token"

    is_expected = False

    def __init__(self, additional_message: str):
        super().__init__(headers={"WWW-Authenticate": "Bearer"}, addition_message=additional_message)


class RecipientsUpdateInvalidStateException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = (
        "All recipient in the state that doesn't allows correction."
    )
    field_name = "envelopeId"

    def __init__(self, envelope_id: str):
        super().__init__(field_value=envelope_id)


class DynamicDocuSignException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Dynamic DocuSign exception which will be raised by DocuSign client"

    def __init__(self, ds_exc: docusign_esign.ApiException, **kwargs):
        body = json.loads(ds_exc.body)
        reason = ds_exc.reason
        error_code = body.get("errorCode")
        ds_exc_message = body.get("message")

        name_error_code = ExcErrorCodeEnum.get_reversed_dict().get(error_code)
        exc_message = ExcErrorMessageEnum.get_dict().get(name_error_code)
        if exc_message:
            message = exc_message
        else:
            message = ds_exc_message if ds_exc_message else self.message

        field_value = kwargs.get("envelope_id") if "envelope_id" in kwargs else None

        self.reason = reason
        self.error_code = error_code
        self.field_name = "envelopeId" if "envelope_id" in kwargs else None

        super().__init__(
            status_code=ds_exc.status,
            message=message,
            field_value=field_value
        )

    @property
    def is_auth_exception(self):
        return (
            self.reason == HTTPStatus.UNAUTHORIZED.phrase
            and self.error_code == ExcErrorCodeEnum.authentication_failed
        )
