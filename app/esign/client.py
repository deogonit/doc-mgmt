import asyncio
from io import BytesIO
from typing import Callable

import aiofiles
import docusign_esign
from docusign_esign.client.api_response import RESTClientObject

from app.config import settings
from app.esign.exception import DynamicDocuSignException
from app.new_relic import wrapp_web_transaction


class DocuSignClient:  # noqa: WPS214
    expires_in = 8 * 60 * 60
    scopes = ["signature", "impersonation"]

    def __init__(self):
        api_client = docusign_esign.ApiClient(host=settings.docu_sign.host)
        api_client.rest_client = RESTClientObject(maxsize=settings.docu_sign.pool_max_size)

        api_client.set_oauth_host_name(settings.docu_sign.authorization_server)
        api_client.request_jwt_user_token(
            client_id=settings.docu_sign.client_id,
            user_id=settings.docu_sign.impersonated_user_id,
            oauth_host_name=settings.docu_sign.authorization_server,
            private_key_bytes=settings.docu_sign.private_key,
            expires_in=self.expires_in,
            scopes=self.scopes,
        )

        self._client = api_client
        self._account_id = settings.docu_sign.account_id
        self._envelopes_api = docusign_esign.EnvelopesApi(self._client)

    async def refresh_access_token(self) -> None:
        await asyncio.to_thread(
            self._client.request_jwt_user_token,
            client_id=settings.docu_sign.client_id,
            user_id=settings.docu_sign.impersonated_user_id,
            oauth_host_name=settings.docu_sign.authorization_server,
            private_key_bytes=settings.docu_sign.private_key,
            expires_in=self.expires_in,
            scopes=self.scopes,
        )

    async def create_envelope(
        self,
        envelope_definition: docusign_esign.EnvelopeDefinition,
    ) -> docusign_esign.EnvelopeSummary:
        return await self._do_request(
            self._envelopes_api.create_envelope,
            account_id=self._account_id,
            envelope_definition=envelope_definition
        )

    async def update_envelope(
        self,
        envelope_id: str,
        envelope_definition: docusign_esign.Envelope,
        resend_envelope: str = "true",
    ) -> docusign_esign.EnvelopeUpdateSummary:
        return await self._do_request(
            self._envelopes_api.update,
            account_id=self._account_id,
            envelope_id=envelope_id,
            envelope=envelope_definition,
            resend_envelope=resend_envelope,
        )

    async def get_envelope(
        self,
        envelope_id: str,
        include: str | None = "recipients,tabs",
    ) -> docusign_esign.EnvelopeDefinition:
        return await self._do_request(
            self._envelopes_api.get_envelope,
            account_id=self._account_id,
            envelope_id=envelope_id,
            include=include,
        )

    async def get_document_by_id(self, document_id: str, envelope_id: str) -> BytesIO:
        # get_document return path to temp file in a memory
        document = await self._do_request(
            self._envelopes_api.get_document,
            account_id=self._account_id,
            document_id=document_id,
            envelope_id=envelope_id,
        )
        async with aiofiles.open(document, mode="rb") as pdf_file:
            read_file = await pdf_file.read()

        return BytesIO(read_file)

    async def get_recipients(self, envelope_id: str) -> docusign_esign.Recipients:
        return await self._do_request(
            self._envelopes_api.list_recipients,
            account_id=self._account_id,
            envelope_id=envelope_id,
        )

    async def update_recipients(self, envelope_id: str, recipients: docusign_esign.Recipients):
        return await self._do_request(
            self._envelopes_api.update_recipients,
            account_id=self._account_id,
            envelope_id=envelope_id,
            recipients=recipients,
        )

    async def list_documents(self, envelope_id: str):
        return await self._do_request(
            self._envelopes_api.list_documents,
            account_id=self._account_id,
            envelope_id=envelope_id,
        )

    async def is_healthy(self) -> bool:
        try:
            await self.refresh_access_token()
        except docusign_esign.ApiException:
            return False

        return True

    async def _do_request(self, method: Callable, **kwargs):
        wrapped_method = wrapp_web_transaction(method)

        try:
            return await asyncio.to_thread(wrapped_method, **kwargs)
        except docusign_esign.ApiException as exc:
            docusign_exc = DynamicDocuSignException(exc, **kwargs)
            if not docusign_exc.is_auth_exception:
                raise docusign_exc

            await self.refresh_access_token()
            return await asyncio.to_thread(wrapped_method, **kwargs)
