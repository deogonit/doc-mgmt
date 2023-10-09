import asyncio
import logging
import time
from pathlib import Path
from typing import cast

from httpx import AsyncClient, HTTPStatusError, TimeoutException
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random

from app.config import settings
from app.esign.client import DocuSignClient
from app.esign.enum import EnvelopeStatusEnum
from app.esign.models.envelope import (
    DocumentItem,
    EnvelopePutItem,
    EnvelopeSearchItem,
    EnvelopeUpdateItem,
    SignerItem,
)
from app.esign.models.envelope_callback import (
    EnvelopeCallbackPutItem,
    EnvelopeCallbackSearchItem,
    EnvelopeCallbackUpdateItem,
)
from app.esign.repositories import EnvelopeCallbackRepository, EnvelopeRepository
from app.esign.schema.webhook import (
    DSWebHookRecipients,
    DSWebhookRedeliverRequest,
    DSWebHookRequest,
    DSWebHookSigner,
)
from app.file_storage.service import FileStorageService


class ESignWebhookService:
    signed_documents_path = Path("signed-documents")
    documents_names_for_skip = {"certificate"}

    def __init__(
        self,
        ds_client: DocuSignClient,
        storage: FileStorageService,
        envelope_repository: EnvelopeRepository,
        envelope_callback_repository: EnvelopeCallbackRepository,
        main_bucket_name: str,
        expiration_date_in_seconds: int
    ) -> None:
        self.ds_client = ds_client
        self.storage = storage
        self.envelope_repository = envelope_repository
        self.envelope_callback_repository = envelope_callback_repository
        self.main_bucket_name = main_bucket_name
        self.expiration_date_in_seconds = expiration_date_in_seconds

        self._logger = logging.getLogger(self.__class__.__name__)

    async def process_webhook(self, webhook_schema: DSWebHookRequest) -> None:
        envelope = await self.envelope_repository.get_item(
            EnvelopeSearchItem(envelope_id=webhook_schema.envelope_id)
        )

        signers: list[SignerItem] = [
            SignerItem(
                email=signer.email,
                recipient_id=signer.recipient_id,
                recipient_id_guid=signer.recipient_id_guid,
                status=signer.status,
            )
            for signer in webhook_schema.recipients.signers
        ]

        # We can get information about documents from webhook (see EventNotification object in event_notification
        # property), but webhook will contain entire document in base64 encoded version. In this case we will log
        # ALL entire document in output or in NewRelic. This is not secure and not good approach.
        list_documents = await self.ds_client.list_documents(webhook_schema.envelope_id)

        documents = [
            DocumentItem(
                document_id=document.document_id,
                document_id_guid=document.document_id_guid,
                name=document.name,
                uri=document.uri,
                order=document.order,
            )
            for document in list_documents.envelope_documents
            if document.document_id not in self.documents_names_for_skip
        ]

        documents = await self._store_signed_documents_in_bucket(webhook_schema.envelope_id, documents)
        expiration_time = (
            int(time.time()) + self.expiration_date_in_seconds
            if webhook_schema.status in EnvelopeStatusEnum.get_statuses_to_expiration()
            else None
        )
        envelope_put_object = EnvelopePutItem(
            envelope_id=webhook_schema.envelope_id,
            envelope_status=webhook_schema.status,
            status_changed_date_time=webhook_schema.status_changed_date_time,
            signers=signers,
            documents=documents,
            expiration_time=expiration_time,
        )
        if envelope:
            envelope_update_object = EnvelopeUpdateItem(
                envelope_id=webhook_schema.envelope_id,
                envelope_status=webhook_schema.status,
                status_changed_date_time=webhook_schema.status_changed_date_time,
                signers=signers,
                documents=documents,
                expiration_time=expiration_time
            )
            await self.envelope_repository.update_item(envelope_update_object)
        else:
            await self.envelope_repository.put_item(envelope_put_object)

        envelope_callback = await self.envelope_callback_repository.get_item(
            EnvelopeCallbackSearchItem(envelope_id=webhook_schema.envelope_id)
        )
        if envelope_callback:
            await self.envelope_callback_repository.update_item(
                EnvelopeCallbackUpdateItem(
                    envelope_id=webhook_schema.envelope_id,
                    expiration_time=expiration_time
                )
            )
            await self._send_notification_to_application(
                envelope_callback.callback_url,
                webhook_schema.envelope_id,
                webhook_schema.status.value,
                envelope_put_object.dict(exclude={"status_changed_date_time", "created_at"}, by_alias=True)
            )

    async def redeliver_webhook_event(
        self,
        envelope_id: str,
        webhook_redeliver_schema: DSWebhookRedeliverRequest
    ) -> None:
        original_envelope_definition = await self.ds_client.get_envelope(
            envelope_id,
            include="extensions,recipients"
        )
        envelope_callback = await self.envelope_callback_repository.get_item(
            EnvelopeCallbackSearchItem(envelope_id=envelope_id)
        )

        if webhook_redeliver_schema.callback_url:
            if envelope_callback:
                await self.envelope_callback_repository.update_item(
                    EnvelopeCallbackUpdateItem(
                        envelope_id=envelope_id,
                        callback_url=webhook_redeliver_schema.callback_url,
                    )
                )
            else:
                await self.envelope_callback_repository.put_item(
                    EnvelopeCallbackPutItem(
                        envelope_id=envelope_id,
                        callback_url=webhook_redeliver_schema.callback_url,
                        expiration_time=None,
                    )
                )

        signers = [
            DSWebHookSigner(
                email=ds_signer.email,
                status=ds_signer.status,
                recipient_id=ds_signer.recipient_id,
                recipient_id_guid=ds_signer.recipient_id_guid,
            )
            for ds_signer in original_envelope_definition.recipients.signers
        ]
        webhook_schema = DSWebHookRequest(
            status_changed_date_time=original_envelope_definition.status_changed_date_time,
            status=original_envelope_definition.status,
            envelope_id=original_envelope_definition.envelope_id,
            recipients=DSWebHookRecipients(signers=signers)
        )

        await self.process_webhook(webhook_schema)

    @retry(
        reraise=True,
        wait=wait_random(min=settings.docu_sign.min_wait, max=settings.docu_sign.max_wait),
        stop=stop_after_attempt(settings.docu_sign.max_attempt),
        retry=retry_if_exception_type(TimeoutException),
    )
    async def _send_notification_to_application(
        self,
        callback_url: str,
        envelope_id: str,
        envelope_status: str,
        object_to_send: dict
    ) -> None:
        async with AsyncClient() as client:
            try:
                response = await client.post(
                    url=callback_url,
                    json=object_to_send,
                    timeout=settings.docu_sign.max_timeout
                )
            except TimeoutException:  # noqa: WPS329
                self._logger.error(f"TimeoutException has been raised when send request to {callback_url}")
                raise

            try:
                response.raise_for_status()
            except HTTPStatusError as http_exc:
                exc_message = str(http_exc)
                log_message = (
                    f"Error when trying to send data to host {callback_url}. "
                    + f"Envelope with id {envelope_id} and status {envelope_status}."
                    + f"Exception: {exc_message}"
                )
                self._logger.error(log_message)

    async def _store_signed_documents_in_bucket(
        self,
        envelope_id: str,
        documents: list[DocumentItem]
    ) -> list[DocumentItem]:
        store_document_tasks = [
            self._store_signed_document(envelope_id, document)
            for document in documents
        ]
        stored_documents = await asyncio.gather(*store_document_tasks)

        return cast(list[DocumentItem], stored_documents)

    async def _store_signed_document(self, envelope_id: str, document: DocumentItem) -> DocumentItem:
        downloaded_document = await self.ds_client.get_document_by_id(
            envelope_id=envelope_id, document_id=document.document_id
        )

        file_path = str(self.signed_documents_path / envelope_id / f"{document.document_id_guid}.pdf")
        await self.storage.upload_file(self.main_bucket_name, file_path, downloaded_document)

        document.document_bucket_name = self.main_bucket_name
        document.document_path = file_path
        return document
