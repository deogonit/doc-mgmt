from app.base.schema import ApiBaseModel
from app.health_check.enum import HealthStatusEnum


class HealthStatusResponse(ApiBaseModel):
    status: HealthStatusEnum = HealthStatusEnum.healthy


class ReadyServicesResponse(ApiBaseModel):
    s3: HealthStatusEnum
    dynamodb: HealthStatusEnum
    docusign: HealthStatusEnum
    gotenberg: HealthStatusEnum


class ReadyStatusResponse(HealthStatusResponse):
    services: ReadyServicesResponse
