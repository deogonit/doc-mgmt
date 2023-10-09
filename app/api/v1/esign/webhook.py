import datetime
import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from app.api.logging_route import LoggingRoute
from app.base.exception import merge_exception_descriptions
from app.container import Container
from app.esign.auth import AbstractAuthentication
from app.esign.exception import (
    DynamicDocuSignException,
    EnvelopeInDbDoesntExistException,
    InvalidAuthenticationCreds,
)
from app.esign.schema.webhook import DSWebHookCreatedAtRequest, DSWebHookRequest
from app.esign.services import ESignWebhookService
from app.file_storage.exception import DynamicS3Exception
from app.new_relic import TransactionGroupName, track_transaction

ESIGN_WEBHOOK_SERVICE_DEPEND = Depends(Provide[Container.esign_webhook_service])
WEBHOOK_AUTH_SERVICE_DEPEND = Depends(Provide[Container.webhook_auth_service])
CONFIG_DEPEND = Depends(Provide(Container.config))
AUTHORIZATION_HEADER = Header(None, alias="Authorization")

CHANGED_AUTH_SCHEMA_DATE = datetime.datetime(2023, 5, 24, tzinfo=datetime.timezone.utc)  # noqa: WPS432


@inject
async def validate_webhook_jwt_token(
    request: Request,
    authorization_header: str | None = AUTHORIZATION_HEADER,
    config_depend=CONFIG_DEPEND,
    webhook_auth_service: AbstractAuthentication = WEBHOOK_AUTH_SERVICE_DEPEND,
):
    # This code block skip auth validation for envelopes which had been created before 05/24/23 with hmac
    # Needs to remove this code after two - three weeks.
    # Issue: https://github.com/CoverWhale/prime-doc-mgmt-k8s/issues/395
    webhook_data = await request.json()
    webhook_created_at_schema = DSWebHookCreatedAtRequest(**webhook_data)
    if webhook_created_at_schema.created_date_time <= CHANGED_AUTH_SCHEMA_DATE:
        logger = logging.getLogger("validate_webhook_jwt_token")
        logger.info(
            f"Skip auth validation for envelope: {webhook_created_at_schema.envelope_id}, "
            + f"created_at: {webhook_created_at_schema.created_date_time}"
        )
        return

    if not (config_depend["auth_docu_sign"]["domain"] and config_depend["auth_docu_sign"]["api_audience"]):
        return

    scheme, credentials = get_authorization_scheme_param(authorization_header)
    if not (authorization_header and scheme and credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    webhook_auth_service.has_access(credentials)


router = APIRouter(
    prefix="/esign",
    tags=["esign"],
    route_class=LoggingRoute,
    dependencies=[Depends(validate_webhook_jwt_token)],
)


@router.post(
    "/webhook",
    response_model={},
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicS3Exception,
        DynamicDocuSignException,
        InvalidAuthenticationCreds,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def process_webhook(
    web_hook_schema: DSWebHookRequest,
    esign_webhook_service: ESignWebhookService = ESIGN_WEBHOOK_SERVICE_DEPEND,
) -> dict:
    """
    Endpoint for processing webhook which receive changes from DocuSign.
    In deployed version the endpoint is secured using x-docusigm-signature-1.

    **Algorithm**:
    1. Try to get the envelope from the Envelope table in DynamoDB. If the envelope doesn't exist, go to second point.
    If the envelope exists and the status changed the time of this envelope is bigger than the status
    changed time of the new event application should return nothing.
    2. Fetch all documents from the envelope.
    3. If the status of the envelope is completed, the application should save all documents in an S3 bucket.
    4. Application should save updated information about the envelope into DynamoDB.
    5. If the envelope has a callback URL, the application should send information with changes to the client
    with the URL.

    **Args**:
    - **web_hook_schema**: DSWebHookRequest object with all information about signers, documents, status, and envelope
    id and status changed time.
    - **esign_webhook_service**: ESignService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - empty object
    """
    await esign_webhook_service.process_webhook(web_hook_schema)
    return {}
