import asyncio

from botocore.exceptions import EndpointConnectionError
from pydantic import BaseModel
from types_aiobotocore_dynamodb import DynamoDBClient

from app.api_client.gotenberg_api_client import GotenbergApiClient
from app.esign.client import DocuSignClient
from app.file_storage.service import FileStorageService
from app.health_check.enum import HealthServiceEnum, HealthStatusEnum
from app.health_check.schema import HealthStatusResponse, ReadyStatusResponse


class StatusCheckResult(BaseModel):
    service: HealthServiceEnum
    status: HealthStatusEnum


class HealthCheckService:
    def __init__(
        self,
        storage_service: FileStorageService,
        main_bucket_name: str,
        dynamodb_client: DynamoDBClient,
        dynamodb_table_names: list[str],
        docusign_client: DocuSignClient,
        gotenberg_api_client: GotenbergApiClient,
    ):
        self._storage_service = storage_service
        self._main_bucket_name = main_bucket_name

        self._dynamodb_client = dynamodb_client
        self._dynamodb_table_names = dynamodb_table_names

        self._docusign_client = docusign_client

        self._gotenberg_api_client = gotenberg_api_client

    async def get_live_status(self):
        return HealthStatusResponse(
            status=HealthStatusEnum.healthy
        )

    async def get_ready_status(self) -> ReadyStatusResponse:
        ready_tasks = [
            self._check_s3(),
            self._check_dynamodb(),
            self._check_docusign(),
            self._check_gotenberg(),
        ]
        status_checks = await asyncio.gather(*ready_tasks)

        services = {status_check.service.name: status_check.status for status_check in status_checks}

        if HealthStatusEnum.unhealthy in services.values():
            status = HealthStatusEnum.unhealthy
        elif HealthStatusEnum.misconfigured in services.values():
            status = HealthStatusEnum.misconfigured
        else:
            status = HealthStatusEnum.healthy

        return ReadyStatusResponse(
            status=status,
            services=services,
        )

    async def _check_s3(self):
        try:
            is_bucket_exists = await self._storage_service.is_bucket_exists(self._main_bucket_name)
        except EndpointConnectionError:
            return StatusCheckResult(
                service=HealthServiceEnum.s3,
                status=HealthStatusEnum.unhealthy,
            )

        return StatusCheckResult(
            service=HealthServiceEnum.s3,
            status=HealthStatusEnum.healthy if is_bucket_exists else HealthStatusEnum.misconfigured,
        )

    async def _check_dynamodb(self):
        describe_table_tasks = [
            self._dynamodb_client.describe_table(TableName=table_name)
            for table_name in self._dynamodb_table_names
        ]

        try:
            await asyncio.gather(*describe_table_tasks)
        except self._dynamodb_client.exceptions.ResourceNotFoundException:
            status = HealthStatusEnum.misconfigured
        except EndpointConnectionError:
            status = HealthStatusEnum.unhealthy
        else:
            status = HealthStatusEnum.healthy

        return StatusCheckResult(
            service=HealthServiceEnum.dynamodb,
            status=status,
        )

    async def _check_docusign(self):
        status = await self._docusign_client.is_healthy()
        return StatusCheckResult(
            service=HealthServiceEnum.docusign,
            status=HealthStatusEnum.healthy if status else HealthStatusEnum.unhealthy,
        )

    async def _check_gotenberg(self):
        status = await self._gotenberg_api_client.is_healthy()
        return StatusCheckResult(
            service=HealthServiceEnum.gotenberg,
            status=HealthStatusEnum.healthy if status else HealthStatusEnum.unhealthy,
        )
