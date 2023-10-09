import asyncio
import base64
import datetime
import logging
import uuid

import docusign_esign

from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.exception import DocumentDoesntExistException, EnvelopeInCreatingStatusException
from app.esign.models.envelope import EnvelopeItemModel, EnvelopePutItem
from app.esign.models.envelope_callback import EnvelopeCallbackPutItem, EnvelopeCallbackSearchItem
from app.esign.repositories import EnvelopeCallbackRepository, EnvelopeRepository
from app.esign.schema.envelope import DSDocumentRequest, DSEnvelopeIdResponse, DSEnvelopeRequest
from app.esign.services.builders import build_esign_tabs, build_event_notification
from app.file_storage.service import FileStorageService


class ESignEnvelopeCreateService:
    def __init__(
        self,
        ds_client: DocuSignClient,
        storage: FileStorageService,
        envelope_repository: EnvelopeRepository,
        envelope_callback_repository: EnvelopeCallbackRepository,
        webhook_url: str | None,
    ) -> None:
        self.ds_client = ds_client
        self.storage = storage
        self.envelope_repository = envelope_repository
        self.envelope_callback_repository = envelope_callback_repository
        self.webhook_url = webhook_url

        self._logger = logging.getLogger(self.__class__.__name__)

    async def create_envelope(self, ds_envelope_schema: DSEnvelopeRequest) -> DSEnvelopeIdResponse:
        schema_unique_id = str(uuid.uuid4())
        for number_signer, signer in enumerate(ds_envelope_schema.signers, start=1):
            signer_json = signer.json()
            self._logger.info(f"SchemaID {schema_unique_id} | Signer #{number_signer} {signer_json}")

        envelope_definition = await self.build_envelope_definition(ds_envelope_schema)

        creation_result = await self.ds_client.create_envelope(envelope_definition)

        envelope_put_object = EnvelopePutItem(
            envelope_id=creation_result.envelope_id,
            envelope_status=EnvelopeStatusEnum.custom_creating.value,
            status_changed_date_time=datetime.datetime.utcnow(),
            expiration_time=None
        )
        await self.envelope_repository.put_item(envelope_put_object)

        if ds_envelope_schema.callback_url:
            await self.envelope_callback_repository.put_item(
                EnvelopeCallbackPutItem(
                    envelope_id=creation_result.envelope_id,
                    callback_url=ds_envelope_schema.callback_url,
                    expiration_time=None,
                )
            )

        return DSEnvelopeIdResponse(envelope_id=creation_result.envelope_id)

    async def clone_envelope(self, original_envelope_id: str):
        original_envelope_db = await self.envelope_repository.get_envelope(original_envelope_id)

        if original_envelope_db.envelope_status == EnvelopeStatusEnum.custom_creating.value:
            raise EnvelopeInCreatingStatusException(original_envelope_db.envelope_id)

        original_envelope_definition = await self.ds_client.get_envelope(
            original_envelope_id,
            include="extensions,recipients,tabs",
        )
        envelope_definition = await self._clone_envelope_definition(original_envelope_definition, original_envelope_db)

        creation_result = await self.ds_client.create_envelope(envelope_definition)
        envelope_put_object = EnvelopePutItem(
            envelope_id=creation_result.envelope_id,
            envelope_status=EnvelopeStatusEnum.custom_creating.value,
            status_changed_date_time=datetime.datetime.utcnow(),
            expiration_time=None
        )
        await self.envelope_repository.put_item(envelope_put_object)

        envelope_callback = await self.envelope_callback_repository.get_item(
            EnvelopeCallbackSearchItem(envelope_id=original_envelope_id)
        )
        if envelope_callback:
            await self.envelope_callback_repository.put_item(
                EnvelopeCallbackPutItem(
                    envelope_id=creation_result.envelope_id,
                    callback_url=envelope_callback.callback_url,
                    expiration_time=None
                )
            )

        return DSEnvelopeIdResponse(envelope_id=creation_result.envelope_id)

    async def build_envelope_definition(
        self,
        ds_envelope_schema: DSEnvelopeRequest
    ) -> docusign_esign.EnvelopeDefinition:
        download_tasks = [
            self._get_document_file(document)
            for document in ds_envelope_schema.documents
        ]
        documents = await asyncio.gather(*download_tasks)

        signers: list[docusign_esign.Signer] = []
        workflow_steps: list[docusign_esign.WorkflowStep] = []
        for signer_index, signer_schema in enumerate(ds_envelope_schema.signers, start=1):
            email_notification = None
            if signer_schema.email_subject or signer_schema.email_body:
                email_notification = docusign_esign.RecipientEmailNotification(
                    email_subject=signer_schema.email_subject,
                    email_body=signer_schema.email_body,
                )

            signers.append(
                docusign_esign.Signer(
                    recipient_id=signer_schema.recipient_id,
                    email=signer_schema.email,
                    name=signer_schema.name,
                    routing_order=signer_schema.order,
                    email_notification=email_notification,
                    tabs=build_esign_tabs(signer_schema.tabs),
                )
            )

            if signer_index != 1 and signer_schema.should_pause_signing_before:
                workflow_steps.append(
                    docusign_esign.WorkflowStep(
                        action="pause_before",
                        trigger_on_item="routing_order",
                        item_id=signer_index
                    )
                )

        recipients = docusign_esign.Recipients(signers=signers)
        workflow = docusign_esign.Workflow(workflow_steps=workflow_steps) if workflow_steps else None

        return docusign_esign.EnvelopeDefinition(
            email_subject=ds_envelope_schema.email_subject,
            email_blurb=ds_envelope_schema.email_body,
            documents=documents,
            recipients=recipients,
            status=EnvelopeStatusEnum.sent.value,
            event_notification=build_event_notification(self.webhook_url),
            workflow=workflow
        )

    async def _clone_envelope_definition(
        self,
        envelope_definition: docusign_esign.EnvelopeDefinition,
        envelope_db: EnvelopeItemModel,
    ) -> docusign_esign.EnvelopeDefinition:
        document_schemas = [
            DSDocumentRequest(
                document_id=document_db.document_id,
                name=document_db.name,
                bucket_name=document_db.document_bucket_name,
                document_path=document_db.document_path
            ) for document_db in envelope_db.documents
        ] if envelope_db.documents else []

        download_tasks = [
            self._get_document_file(document)
            for document in document_schemas
        ]
        documents = await asyncio.gather(*download_tasks)

        remaining_signer_ids = [
            signer.recipient_id_guid
            for signer in envelope_db.signers
            if signer.status != "completed"
        ] if envelope_db.signers else []

        signers = [
            signer
            for signer in envelope_definition.recipients.signers
            if signer.recipient_id_guid in remaining_signer_ids
        ]
        recipients = docusign_esign.Recipients(signers=signers)

        return docusign_esign.EnvelopeDefinition(
            email_subject=envelope_definition.email_subject,
            email_blurb=envelope_definition.email_blurb,
            documents=documents,
            recipients=recipients,
            status=EnvelopeStatusEnum.sent.value,
            event_notification=build_event_notification(self.webhook_url),
        )

    async def _get_document_file(self, document_schema: DSDocumentRequest) -> docusign_esign.Document:
        document_file = await self.storage.download_file(document_schema.bucket_name, document_schema.document_path)

        if not document_file:
            raise DocumentDoesntExistException(document_schema.document_path)

        encoded_document = base64.b64encode(document_file.read()).decode("ascii")

        return docusign_esign.Document(
            document_id=document_schema.document_id,
            name=document_schema.name,
            document_base64=encoded_document,
            file_extension="pdf",
        )
