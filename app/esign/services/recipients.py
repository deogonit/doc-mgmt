import logging

import docusign_esign

from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.exception import (
    EnvelopeInCreatingStatusException,
    RecipientsUpdateInvalidStateException,
)
from app.esign.repositories import EnvelopeRepository
from app.esign.schema.update_signers import (
    DSUpdateSignersItemResponse,
    DSUpdateSignersRequest,
    DSUpdateSignersResponse,
)


class ESignRecipientsService:
    def __init__(
        self,
        ds_client: DocuSignClient,
        envelope_repository: EnvelopeRepository,
    ) -> None:
        self.ds_client = ds_client
        self.envelope_repository = envelope_repository

        self._logger = logging.getLogger(self.__class__.__name__)

    async def update_signers(
        self,
        envelope_id: str,
        update_signers_schema: DSUpdateSignersRequest
    ) -> DSUpdateSignersResponse:
        envelope = await self.envelope_repository.get_envelope(envelope_id)

        if envelope.envelope_status == EnvelopeStatusEnum.custom_creating.value:
            raise EnvelopeInCreatingStatusException(envelope.envelope_id)

        recipients = docusign_esign.Recipients(
            signers=[
                docusign_esign.Signer(**signer.dict(exclude_none=True))
                for signer in update_signers_schema.signers
            ],
        )
        recipient_update_summary = await self.ds_client.update_recipients(envelope_id, recipients)

        failed_recipient_updates = {
            recipient_update_result.recipient_id: recipient_update_result.error_details.message
            for recipient_update_result in recipient_update_summary.recipient_update_results
            if recipient_update_result.error_details is not None
        }

        if len(failed_recipient_updates) == len(recipient_update_summary.recipient_update_results):
            raise RecipientsUpdateInvalidStateException(envelope_id)

        recipients_info = await self.ds_client.get_recipients(envelope_id)

        return DSUpdateSignersResponse(
            envelope_id=envelope_id,
            signers=[
                DSUpdateSignersItemResponse(
                    **signer_info.to_dict(),
                    update_error=failed_recipient_updates.get(signer_info.recipient_id),
                )
                for signer_info in recipients_info.signers
            ],
        )
