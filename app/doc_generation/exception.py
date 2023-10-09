from fastapi import status

from app.base.exception import BaseHTTPException


class FileDoesntExistException(BaseHTTPException):
    status_code = status.HTTP_404_NOT_FOUND
    message = "File by path does not exist"

    def __init__(self, file_path: str):
        super().__init__(field_value=file_path)


class UnsupportedTemplateExtensionException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Unsupported template extension"
    field_name = "templatePath"

    def __init__(self, extension: str):
        super().__init__(field_value=extension)


class MissingVariablesInTemplateException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Not all required template variables were provided."
    field_name = "templateVariables"

    def __init__(self, missing_variables: str, additional_message: str | None = None):
        super().__init__(field_value=missing_variables, addition_message=additional_message)


class FolderAccessForbiddenException(BaseHTTPException):
    status_code = status.HTTP_403_FORBIDDEN
    message = "Access to folder is forbidden"
    field_name = "templatePath"

    def __init__(self, template_path: str):
        super().__init__(field_value=template_path)


class FileContentDoesntExistInRegistryException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "File doesn't exist in cache (registry). Repeat request"


class InvalidTemplateException(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Cannot use template, because it's invalid"

    is_expected = False

    field_name = "templatePath"

    def __init__(self, template_path: str) -> None:
        super().__init__(field_value=template_path)


class IncorrectProcessorState(BaseHTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "DocumentProcessor is in incorrect state"

    is_expected = False

    def __init__(self, field_name: str) -> None:
        super().__init__(addition_message=f"Incorrect field: {field_name}")
