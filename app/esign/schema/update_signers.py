from pydantic import EmailStr

from app.base.schema import ApiBaseModel


class DSUpdateSignersItemRequest(ApiBaseModel):
    recipient_id: str
    email: EmailStr | None
    name: str | None


class DSUpdateSignersRequest(ApiBaseModel):
    signers: list[DSUpdateSignersItemRequest]


class DSUpdateSignersItemResponse(ApiBaseModel):
    recipient_id: str
    recipient_id_guid: str
    email: EmailStr
    name: str
    update_error: str | None


class DSUpdateSignersResponse(ApiBaseModel):
    envelope_id: str
    signers: list[DSUpdateSignersItemResponse]
