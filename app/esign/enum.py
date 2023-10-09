from app.base.components import BaseEnum


class EnvelopeStatusEnum(BaseEnum):
    """
    The list of envelope statuses
    https://developers.docusign.com/docs/esign-rest-api/esign101/concepts/envelopes/status-codes/
    """

    authoritativecopy = "authoritativecopy"
    completed = "completed"
    correct = "correct"
    created = "created"
    declined = "declined"
    deleted = "deleted"
    delivered = "delivered"
    sent = "sent"
    signed = "signed"
    template = "template"
    timedout = "timedout"
    transfercompleted = "transfercompleted"
    voided = "voided"

    custom_creating = "custom:creating"

    @classmethod
    def get_statuses_to_expiration(cls) -> tuple[str, str, str, str]:
        return (
            EnvelopeStatusEnum.completed.value,
            EnvelopeStatusEnum.declined.value,
            EnvelopeStatusEnum.deleted.value,
            EnvelopeStatusEnum.voided.value,
        )


class ExcErrorCodeEnum(BaseEnum):
    authentication_failed = "USER_AUTHENTICATION_FAILED"
    resend_invalid_state = "EDIT_LOCK_INVALID_STATE_FOR_LOCK"
    void_invalid_state = "ENVELOPE_CANNOT_VOID_INVALID_STATE"
    envelope_invalid_status = "ENVELOPE_INVALID_STATUS"
    envelope_does_not_exist = "ENVELOPE_DOES_NOT_EXIST"


class ExcErrorMessageEnum(BaseEnum):
    authentication_failed = ""
    resend_invalid_state = "Only envelope in the 'Created', 'Sent' or 'Delivered' states may be resent."
    void_invalid_state = "Only envelope in the 'Sent' or 'Delivered' states may be voided."
    envelope_invalid_status = (
        "Signers can be changed only for envelope in the 'Created', 'Sent', 'Delivered', 'Correct' status"
    )
    envelope_does_not_exist = "Envelop by id does not exist"
