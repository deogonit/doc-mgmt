from app.base.components import BaseEnum


class HealthServiceEnum(BaseEnum):
    s3 = "s3"
    dynamodb = "dynamodb"
    docusign = "docusign"
    gotenberg = "gotenberg"


class HealthStatusEnum(BaseEnum):
    healthy = "healthy"
    unhealthy = "unhealthy"
    misconfigured = "misconfigured"
