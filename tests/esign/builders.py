import uuid
from collections import namedtuple
from datetime import datetime

from app.base.constants import DatetimeFormats
from app.esign.enum import EnvelopeStatusEnum

FIRST_ORDER_NUMBER = 1
LAST_ORDER_NUMBER = 999

DocumentItemResponseTuple = namedtuple(
    "DocumentItemResponseTuple",
    [
        "document_id",
        "document_id_guid",
        "name",
        "uri",
        "order",
    ]
)
ListDocumentsResponseTuple = namedtuple("ListDocumentsResponseTuple", "envelope_documents")
SignerItemResponseTuple = namedtuple(
    "SignerItemResponseTuple",
    [
        "email",
        "recipient_id",
        "recipient_id_guid",
        "status"
    ]
)
EnvelopeRecipientsResponseTyple = namedtuple("EnvelopeRecipientsResponseTyple", "signers")
EnvelopeResponseTyple = namedtuple(
    "EnvelopeResponseTyple",
    [
        "envelope_id",
        "status_changed_date_time",
        "status",
        "recipients",
    ]
)
EnvelopeCreateResponseTuple = namedtuple("EnvelopeCreateResponseTuple", "envelope_id")


def build_webhook_event(
    *,
    status: EnvelopeStatusEnum | str = EnvelopeStatusEnum.sent,
    changed_date_time: datetime | None = None,
    envelope_id: str | None = None,
) -> dict:
    envelope_id = envelope_id or str(uuid.uuid4())
    status_changed_date_time = changed_date_time or datetime.utcnow()
    status = status.value if isinstance(status, EnvelopeStatusEnum) else status

    return {
        "status": status,
        "createdDateTime": "2023-05-25T01:39:58.087Z",
        "statusChangedDateTime": status_changed_date_time.strftime(DatetimeFormats.utc_string_format),
        "envelopeId": envelope_id,
        "recipients": {
            "signers": [
                {
                    "email": "string",
                    "status": "string",
                    "recipientId": "string",
                    "recipientIdGuid": "string",
                }
            ]
        }
    }


def build_envelope_documents_response(envelope_id: str):
    document_guid = str(uuid.uuid4())
    certificate_guid = str(uuid.uuid4())
    envelope_documents = [
        DocumentItemResponseTuple(
            document_id="1",
            document_id_guid=document_guid,
            name="Main document",
            uri=f"/envelopes/{envelope_id}/documents/1",
            order=FIRST_ORDER_NUMBER
        ),
        DocumentItemResponseTuple(
            document_id="certificate",
            document_id_guid=certificate_guid,
            name="Summary",
            uri=f"/envelopes/{envelope_id}/documents/certificate",
            order=LAST_ORDER_NUMBER
        )
    ]
    return ListDocumentsResponseTuple(envelope_documents=envelope_documents)


def build_envelope_recipients_response(envelope_id: str):
    signers = [
        SignerItemResponseTuple(
            email="email@maildoesntexists.com",
            recipient_id="1",
            recipient_id_guid="a4f43273-19b4-477f-a4b5-38b134e8afce",
            status=EnvelopeStatusEnum.sent.value,
        )
    ]
    envelope_recipients = EnvelopeRecipientsResponseTyple(signers=signers)
    status_changed_date_time = datetime.utcnow().strftime(DatetimeFormats.utc_string_format)

    return EnvelopeResponseTyple(
        envelope_id=envelope_id,
        status=EnvelopeStatusEnum.sent.value,
        status_changed_date_time=status_changed_date_time,
        recipients=envelope_recipients
    )
