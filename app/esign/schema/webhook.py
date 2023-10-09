from datetime import datetime

from pydantic import AnyHttpUrl

from app.base.schema import ApiBaseModel
from app.esign.enum import EnvelopeStatusEnum


class DSWebHookSigner(ApiBaseModel):
    email: str
    status: str
    recipient_id: str
    recipient_id_guid: str


class DSWebHookRecipients(ApiBaseModel):
    signers: list[DSWebHookSigner]


class DSWebHookRequest(ApiBaseModel):
    status_changed_date_time: datetime
    status: EnvelopeStatusEnum
    envelope_id: str
    recipients: DSWebHookRecipients


class DSWebHookCreatedAtRequest(ApiBaseModel):
    envelope_id: str
    created_date_time: datetime


class DSWebhookRedeliverRequest(ApiBaseModel):
    callback_url: AnyHttpUrl | None = None
