from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.api.logging_route import LoggingRoute
from app.auth import verify_api_key
from app.base.exception import merge_exception_descriptions
from app.container import Container
from app.esign.exception import (
    DocumentDoesntExistException,
    DynamicDocuSignException,
    EnvelopeInCreatingStatusException,
    EnvelopeInDbDoesntExistException,
    RecipientsUpdateInvalidStateException,
)
from app.esign.schema.envelope import (
    DSEnvelopeIdResponse,
    DSEnvelopeRequest,
    DSEnvelopeResponse,
    DSEnvelopeVoidRequest,
)
from app.esign.schema.update_signers import DSUpdateSignersRequest, DSUpdateSignersResponse
from app.esign.schema.webhook import DSWebhookRedeliverRequest
from app.esign.services import ESignEnvelopeService
from app.esign.services.envelope_create import ESignEnvelopeCreateService
from app.esign.services.recipients import ESignRecipientsService
from app.esign.services.webhook import ESignWebhookService
from app.file_storage.exception import DynamicS3Exception
from app.new_relic import TransactionGroupName, track_transaction

ESIGN_ENVELOPE_SERVICE_DEPEND = Depends(Provide[Container.esign_envelope_service])
ESIGN_ENVELOPE_CREATE_SERVICE_DEPEND = Depends(Provide[Container.esign_envelope_create_service])
ESIGN_RECIPIENTS_SERVICE_DEPEND = Depends(Provide[Container.esign_recipients_service])
ESIGN_WEBHOOK_SERVICE_DEPEND = Depends(Provide[Container.esign_webhook_service])

router = APIRouter(
    prefix="/esign",
    tags=["esign"],
    route_class=LoggingRoute,
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/envelope",
    response_model=DSEnvelopeIdResponse,
    responses=merge_exception_descriptions(
        DocumentDoesntExistException,
        DynamicS3Exception,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def create_envelope(
    ds_envelope_schema: DSEnvelopeRequest,
    esign_envelope_create_service: ESignEnvelopeCreateService = ESIGN_ENVELOPE_CREATE_SERVICE_DEPEND,
) -> DSEnvelopeIdResponse:
    """
    Endpoint for creating envelope. An envelope is an object which contains information about:
    - signers and where signer should sign the document;
    - documents which signers should sign;
    - email body which receivers will see in the email;
    - email subject;
    - (optional) callback URL. it's the URL where the doc-mgmt service will send all information about changes in
    the envelope.

    **Algorithm**:
    1. Build an envelope definition.
    2. Send a request with an envelope definition to create a new envelope.
    3. If the callback URL is None, we should save information with the callback URL to EnvelopeCallback into DynamoDB.
    4. Return the object with the envelope ID.

    **Args**:
    - **ds_envelope_schema**: DSEnvelopeRequest object. This object contains all information what for creating envelope
    in DocuSign
    - **esign_envelope_create_service**: ESignEnvelopeCreateService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSEnvelopeIdResponse**: Returns an object with a newly created envelope ID.

    **Raises**:
    - **DocumentDoesntExistException**: Raises an exception, when the document doesn't exist on S3.
    """

    return await esign_envelope_create_service.create_envelope(ds_envelope_schema)


@router.post(
    "/envelope/{envelope_id}/resend",
    response_model=DSEnvelopeIdResponse,
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicDocuSignException,
        EnvelopeInCreatingStatusException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def resend_envelope(
    envelope_id: str,
    esign_envelope_service: ESignEnvelopeService = ESIGN_ENVELOPE_SERVICE_DEPEND,
) -> DSEnvelopeIdResponse:
    """
    Resend email notification about singing for all signers in in-progress state.

    **Algorithm**:
    1. Check that envelope exists in database.
    2. Call DocuSign envelope update endpoint with resend_envelope=true flag.
    5. Return the object with the envelope ID.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **esign_envelope_service**: ESignEnvelopeService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSEnvelopeIdResponse**: Returns an object with a newly created envelope ID.

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    - **DocumentDoesntExistException**: Raises an exception, when the document doesn't exist on S3.
    """

    return await esign_envelope_service.resend_envelope(envelope_id)


@router.get(
    "/envelope/{envelope_id}",
    response_model=DSEnvelopeResponse,
    responses=EnvelopeInDbDoesntExistException.transform_to_description()
)
@track_transaction(TransactionGroupName.esign)
@inject
async def get_envelope(
    envelope_id: str,
    esign_envelope_service: ESignEnvelopeService = ESIGN_ENVELOPE_SERVICE_DEPEND,
) -> DSEnvelopeResponse:
    """
    The simple endpoint return information from the Envelope table from DynamoDB.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **esign_envelope_service**: ESignEnvelopeService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSEnvelopeIdResponse**: Returns an object with all information about signers, documents, status, and
    envelope ID and status changed time

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    """
    return await esign_envelope_service.get_envelope(envelope_id)


@router.put(
    "/envelope/{envelope_id}/signers",
    response_model=DSUpdateSignersResponse,
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicDocuSignException,
        RecipientsUpdateInvalidStateException,
        EnvelopeInCreatingStatusException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def update_signers(
    envelope_id: str,
    update_signers_schema: DSUpdateSignersRequest,
    esign_recipients_service: ESignRecipientsService = ESIGN_RECIPIENTS_SERVICE_DEPEND,
) -> DSUpdateSignersResponse:
    """
    Endpoint for changing email and name of envelope signers.
    Signers can only be changed if the document has not yet been signed or rejected by them.
    Only envelope in 'Created', 'Sent', 'Delivered', 'Correct' status can be updated.

    **Algorithm**:
    1. Update envelope signers.
    2. Get information about current envelope signers by the list_recipients docusign endpoint.
    4. Return the object with current envelope signers and update error details if some signer was failed to update.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **update_signers_schema**: DSUpdateSignersRequest object. Object with signers list.
    - **esign_recipients_service**: ESignRecipientsService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSUpdateSignersResponse**: Returns an object with current envelope signers.

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    - **EnvelopeUpdateInvalidStateException**: Raises an exception, when the envelope is in a non-updatable status.
    - **RecipientsUpdateInvalidStateException**: Raises an exception, when all signers are in a non-updatable status.
    """
    return await esign_recipients_service.update_signers(envelope_id, update_signers_schema)


@router.post(
    "/envelope/{envelope_id}/void",
    response_model=DSEnvelopeIdResponse,
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicDocuSignException,
        EnvelopeInCreatingStatusException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def void_envelope(
    envelope_id: str,
    ds_void_schema: DSEnvelopeVoidRequest,
    esign_envelope_service: ESignEnvelopeService = ESIGN_ENVELOPE_SERVICE_DEPEND,
) -> DSEnvelopeIdResponse:
    """
    Endpoint for voiding an envelope. Voiding cancels all outstanding signing activities.

    **Args**:
    - **ds_void_schema**: DSEnvelopeVoidRequest object with envelope id and status of voiding.
    - **esign_envelope_service**: ESignEnvelopeService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSEnvelopeIdResponse**: Returns an object with a newly created envelope ID.

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    - **EnvelopeVoidInvalidStateException**: Raises an exception, when the envelope can't be voided.
    """

    return await esign_envelope_service.void_envelope(envelope_id, ds_void_schema)


@router.post(
    "/envelope/{envelope_id}/clone",
    response_model=DSEnvelopeIdResponse,
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DocumentDoesntExistException,
        DynamicDocuSignException,
        EnvelopeInCreatingStatusException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def clone_envelope(
    envelope_id: str,
    esign_envelope_create_service: ESignEnvelopeCreateService = ESIGN_ENVELOPE_CREATE_SERVICE_DEPEND,
) -> DSEnvelopeIdResponse:
    """
    Endpoint to clone envelope in terminated state to continue signing process.
    Envelope in 'Created', 'Sent', 'Delivered', 'Correct' status can be updated,
    so this endpoint clones original envelope, takes last state of document with all signatures
    and keeps only signer that have not signed (or if they have declined or voided envelope)

    **Algorithm**:
    1. Get original envelope data from database and original envelope definition from DocuSign.
    2. Clone in code envelope definition (not via DocuSign).
    3. Create new envelope
    4. Store callback url.
    5. Return the object with the envelope ID.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **esign_envelope_service**: ESignService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - **DSEnvelopeIdResponse**: Returns an object with a newly created envelope ID.

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    - **EnvelopeVoidInvalidStateException**: Raises an exception, when the envelope can't be voided.
    - **DocumentDoesntExistException**: Raises an exception, when the document doesn't exist on S3.
    """

    return await esign_envelope_create_service.clone_envelope(envelope_id)


@router.patch(
    "/envelope/{envelope_id}/unpause",
    response_model={},
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicDocuSignException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def unpause_envelope_workflow(
    envelope_id: str,
    esign_envelope_service: ESignEnvelopeService = ESIGN_ENVELOPE_SERVICE_DEPEND,
) -> dict:
    """
    Endpoint for unpause signing process of recipients.
    The client can pause the signing process for some recipients in create envelope endpoint.
    If you have two or more workflow steps with paused status, you have to use these endpoints
    two or more times.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **esign_envelope_service**: ESignService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - empty object

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    """
    await esign_envelope_service.unpause_envelope(envelope_id)
    return {}


@router.patch(
    "/envelope/{envelope_id}/webhook/redeliver",
    response_model={},
    responses=merge_exception_descriptions(
        EnvelopeInDbDoesntExistException,
        DynamicS3Exception,
        DynamicDocuSignException,
    )
)
@track_transaction(TransactionGroupName.esign)
@inject
async def redeliver_webhook(
    envelope_id: str,
    webhook_redeliver_schema: DSWebhookRedeliverRequest,
    esign_webhook_service: ESignWebhookService = ESIGN_WEBHOOK_SERVICE_DEPEND,
) -> dict:
    """
    Endpoint to resending webhook event through callback url. If EnvelopeCallback doesn't exists in
    DynamoDB, service will create a record in the database.

    **Args**:
    - **envelope_id**: id in uuid format.
    - **webhook_redeliver_schema**: schema which contains callback_url atribute
    - **esign_webhook_service**: ESignWebhookService object. This param will be automatically injected
    by the dependency-injector library.

    **Returns**:
    - empty object

    **Raises**:
    - **EnvelopeInDbDoesntExistException**: Raises an exception, when the envelope doesn't exist in the table.
    - **DynamicDocuSignException**: Raises an dynamic exception, from the DocuSign custom client
    - **DynamicS3Exception**: Raises an dynamic exception, from the DocuSign custom client
    """
    await esign_webhook_service.redeliver_webhook_event(envelope_id, webhook_redeliver_schema)
    return {}
