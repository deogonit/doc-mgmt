import logging

import docusign_esign

from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.exception import EnvelopeInCreatingStatusException
from app.esign.repositories import EnvelopeRepository
from app.esign.schema.envelope import (
    DSEnvelopeIdResponse,
    DSEnvelopeResponse,
    DSEnvelopeVoidRequest,
)


class ESignEnvelopeService:
    def __init__(
        self,
        ds_client: DocuSignClient,
        envelope_repository: EnvelopeRepository,
    ) -> None:
        self.ds_client = ds_client
        self.envelope_repository = envelope_repository

        self._logger = logging.getLogger(self.__class__.__name__)

    async def get_envelope(self, envelope_id: str) -> DSEnvelopeResponse:
        envelope = await self.envelope_repository.get_envelope(envelope_id)

        return DSEnvelopeResponse(**envelope.dict())

    async def resend_envelope(self, envelope_id: str):
        envelope = await self.envelope_repository.get_envelope(envelope_id)

        if envelope.envelope_status == EnvelopeStatusEnum.custom_creating.value:
            raise EnvelopeInCreatingStatusException(envelope.envelope_id)

        creation_result = await self.ds_client.update_envelope(
            envelope_id,
            docusign_esign.Envelope(envelope_id=envelope_id),
            resend_envelope="true",
        )

        return DSEnvelopeIdResponse(envelope_id=creation_result.envelope_id)

    async def void_envelope(self, envelope_id: str, ds_void_schema: DSEnvelopeVoidRequest) -> DSEnvelopeIdResponse:
        envelope = await self.envelope_repository.get_envelope(envelope_id)

        if envelope.envelope_status == EnvelopeStatusEnum.custom_creating.value:
            raise EnvelopeInCreatingStatusException(envelope.envelope_id)

        envelope = docusign_esign.Envelope(
            status="voided",
            voided_reason=ds_void_schema.voided_reason,
        )

        void_result = await self.ds_client.update_envelope(envelope_id, envelope, resend_envelope="false")

        return DSEnvelopeIdResponse(envelope_id=void_result.envelope_id)

    async def unpause_envelope(self, envelope_id: str) -> None:
        envelope = await self.envelope_repository.get_envelope(envelope_id)  # check that envelope exists in db

        envelope = docusign_esign.Envelope(workflow=docusign_esign.Workflow(workflow_status="in_progress"))
        await self.ds_client.update_envelope(envelope_id, envelope, resend_envelope="true")
