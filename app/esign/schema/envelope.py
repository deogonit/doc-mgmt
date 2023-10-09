from datetime import datetime

from pydantic import AnyHttpUrl, EmailStr, Field, validator

from app.base.schema import ApiBaseModel
from app.config import settings
from app.esign.schema import radio_tab as radio_tab_schema
from app.esign.schema import tab as tab_schema


class TabsRequest(ApiBaseModel):
    initial_here_tabs: list[tab_schema.DSInitialHereTab] | None
    sign_here_tabs: list[tab_schema.DSSignHereTab] | None
    full_name_tabs: list[tab_schema.DSFullNameTab] | None
    text_tabs: list[tab_schema.DSTextTab] | None
    email_tabs: list[tab_schema.DSEmailTab] | None
    title_tabs: list[tab_schema.DSTitleTab] | None
    date_tabs: list[tab_schema.DSDateTab] | None
    number_tabs: list[tab_schema.DSNumberTab] | None
    checkbox_tabs: list[radio_tab_schema.DSCheckboxTab] | None
    list_tabs: list[tab_schema.DSListTab] | None
    radio_group_tabs: list[radio_tab_schema.DSRadioGroupTab] | None


class DSDocumentRequest(ApiBaseModel):
    document_id: int
    name: str
    bucket_name: str = settings.storage.main_bucket_name
    document_path: str


class DSSignerRequest(ApiBaseModel):
    recipient_id: int
    email: EmailStr
    name: str
    order: int
    email_subject: str | None = Field(default=None, max_length=100)
    email_body: str | None
    tabs: TabsRequest | None
    should_pause_signing_before: bool = False


class DSEnvelopeRequest(ApiBaseModel):
    email_subject: str = Field(max_length=100)
    email_body: str | None
    documents: list[DSDocumentRequest]
    signers: list[DSSignerRequest]
    callback_url: AnyHttpUrl | None = None

    @validator("documents")
    def check_document_count(cls, documents: list[DSDocumentRequest]) -> list[DSDocumentRequest]:
        if not documents:
            raise ValueError("At least one document has to be provided")

        return documents

    @validator("signers")
    def check_signer_count(cls, signers: list[DSSignerRequest]) -> list[DSSignerRequest]:
        if not signers:
            raise ValueError("At least one signer has to be provided")

        return signers


class DSEnvelopeIdResponse(ApiBaseModel):
    envelope_id: str


class DSEnvelopeVoidRequest(ApiBaseModel):
    voided_reason: str = Field(default="Recipients have been changed")


class DSSignerItemResponse(ApiBaseModel):
    recipient_id: str
    recipient_id_guid: str
    email: str
    status: str


class DSDocumentItemResponse(ApiBaseModel):
    document_id: str
    document_id_guid: str
    name: str
    uri: str
    order: int
    document_path: str | None
    document_bucket_name: str | None


class DSEnvelopeResponse(ApiBaseModel):
    envelope_id: str
    envelope_status: str
    status_changed_date_time: datetime
    signers: list[DSSignerItemResponse] | None
    documents: list[DSDocumentItemResponse] | None
