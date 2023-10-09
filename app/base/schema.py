from humps.main import camelize
from pydantic import BaseModel


class ApiBaseModel(BaseModel):
    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True


class ValidationError(BaseModel):
    message: str
    field: str
    type: str


class BaseErrorDetails(BaseModel):
    message: str | None
    field: str | None
    value: str | None  # noqa: WPS110


class HTTPBaseError(BaseModel):
    details: BaseErrorDetails
