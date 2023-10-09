from typing import Literal

from aioboto3 import Session
from dependency_injector import containers, providers
from types_aiobotocore_dynamodb import DynamoDBClient
from types_aiobotocore_s3 import S3Client

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.config import Settings
from app.doc_generation.repository import DocumentRepository
from app.doc_generation.services import FileConvertorService, FileRegistryService
from app.esign.auth import Auth0Authentication, NoAuthentication
from app.esign.client import DocuSignClient
from app.esign.repositories import EnvelopeCallbackRepository, EnvelopeRepository
from app.esign.services import ESignEnvelopeService, ESignWebhookService
from app.esign.services.envelope_create import ESignEnvelopeCreateService
from app.esign.services.recipients import ESignRecipientsService
from app.file_storage.service import FileStorageService
from app.health_check.service import HealthCheckService


async def init_client(
    session: Session,
    client_name: Literal["s3", "dynamodb"],
    endpoint_url: str | None = None
):
    async with session.client(client_name, endpoint_url=endpoint_url) as client:
        yield client


async def init_gotenberg_api_client(base_url: str, headers: dict):
    gotenberg_api_client = GotenbergApiClient(base_url=base_url, headers=headers)

    yield gotenberg_api_client

    await gotenberg_api_client.close()


def get_way_of_authentication(api_audience: str | None, domain: str | None) -> str:
    return "auth0_authentication" if api_audience and domain else "no_authentication"


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(pydantic_settings=[Settings()])

    boto3_session = providers.Singleton(
        Session,
        aws_access_key_id=config.aws_settings.access_key_id,
        aws_secret_access_key=config.aws_settings.secret_access_key,
    )

    gotenberg_api_client: providers.Resource[GotenbergApiClient] = providers.Resource(
        init_gotenberg_api_client,
        base_url=config.gotenberg.url,
        headers={}
    )

    s3_client: providers.Resource[S3Client] = providers.Resource(
        init_client,
        session=boto3_session,
        client_name="s3",
        endpoint_url=config.storage.endpoint_url
    )
    storage_service: providers.Singleton[FileStorageService] = providers.Singleton(
        FileStorageService,
        s3_client=s3_client,
    )
    registry_service: providers.Singleton[FileRegistryService] = providers.Singleton(
        FileRegistryService,
        file_storage=storage_service,
    )

    dynamodb_client: providers.Resource[DynamoDBClient] = providers.Resource(
        init_client,
        session=boto3_session,
        client_name="dynamodb",
        endpoint_url=config.dynamo_storage.endpoint_url
    )
    document_repository: providers.Singleton[DocumentRepository] = providers.Singleton(
        DocumentRepository,
        dynamodb_client=dynamodb_client,
        table_name=config.dynamo_storage.documents_table_name
    )
    envelope_repository: providers.Singleton[EnvelopeRepository] = providers.Singleton(
        EnvelopeRepository,
        dynamodb_client=dynamodb_client,
        table_name=config.dynamo_storage.envelopes_table_name
    )
    envelope_callback_repository: providers.Singleton[EnvelopeCallbackRepository] = providers.Singleton(
        EnvelopeCallbackRepository,
        dynamodb_client=dynamodb_client,
        table_name=config.dynamo_storage.envelope_callbacks_table_name
    )

    doc_gen_service: providers.Singleton[FileConvertorService] = providers.Singleton(
        FileConvertorService,
        api_client=gotenberg_api_client,
        file_storage=storage_service,
        file_registry=registry_service,
        document_repository=document_repository,
        main_bucket_name=config.storage.main_bucket_name,
        app_version=config.app_version,
        expiration_date_in_seconds=config.dynamo_storage.expiration_date_in_seconds,
        tmp_dir_path=config.doc_gen.tmp_dir_path,
    )

    docusign_client: providers.Singleton[DocuSignClient] = providers.Singleton(
        DocuSignClient,
    )
    esign_envelope_service: providers.Singleton[ESignEnvelopeService] = providers.Singleton(
        ESignEnvelopeService,
        ds_client=docusign_client,
        envelope_repository=envelope_repository,
    )
    esign_envelope_create_service: providers.Singleton[ESignEnvelopeCreateService] = providers.Singleton(
        ESignEnvelopeCreateService,
        ds_client=docusign_client,
        storage=storage_service,
        envelope_repository=envelope_repository,
        envelope_callback_repository=envelope_callback_repository,
        webhook_url=config.docu_sign.webhook_url,
    )
    esign_recipients_service: providers.Singleton[ESignRecipientsService] = providers.Singleton(
        ESignRecipientsService,
        ds_client=docusign_client,
        envelope_repository=envelope_repository,
    )

    webhook_auth_service: providers.Selector = providers.Selector(
        providers.Callable(
            get_way_of_authentication,
            api_audience=config.auth_docu_sign.api_audience,
            domain=config.auth_docu_sign.domain
        ),
        auth0_authentication=providers.Singleton(
            Auth0Authentication,
            audience=config.auth_docu_sign.api_audience,
            domain=config.auth_docu_sign.domain,
        ),
        no_authentication=providers.Singleton(NoAuthentication)
    )

    esign_webhook_service: providers.Singleton[ESignWebhookService] = providers.Singleton(
        ESignWebhookService,
        ds_client=docusign_client,
        storage=storage_service,
        envelope_repository=envelope_repository,
        envelope_callback_repository=envelope_callback_repository,
        main_bucket_name=config.storage.main_bucket_name,
        expiration_date_in_seconds=config.dynamo_storage.expiration_date_in_seconds,
    )

    health_check_service: providers.Singleton[HealthCheckService] = providers.Singleton(
        HealthCheckService,
        dynamodb_client=dynamodb_client,
        dynamodb_table_names=providers.List(
            config.dynamo_storage.documents_table_name,
            config.dynamo_storage.envelopes_table_name,
            config.dynamo_storage.envelope_callbacks_table_name,
        ),
        storage_service=storage_service,
        main_bucket_name=config.storage.main_bucket_name,
        docusign_client=docusign_client,
        gotenberg_api_client=gotenberg_api_client,
    )

    wiring_config = containers.WiringConfiguration(
        packages=[
            "app.api",
        ]
    )
