from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Response, status

from app.api.logging_route import LoggingRoute
from app.container import Container
from app.health_check.enum import HealthStatusEnum
from app.health_check.schema import HealthStatusResponse, ReadyStatusResponse
from app.health_check.service import HealthCheckService
from app.new_relic import ignore_transaction

HEALTH_CHECK_SERVICE_DEPEND = Depends(Provide[Container.health_check_service])

router = APIRouter(
    prefix="",
    tags=["health"],
    route_class=LoggingRoute,
)


@router.get(
    "/health",
    response_model=HealthStatusResponse,
)
@ignore_transaction
@inject
async def get_live_status(
    health_check_service: HealthCheckService = HEALTH_CHECK_SERVICE_DEPEND,
) -> HealthStatusResponse:
    """
    Endpoint for checking that application is working and returns a response.
    """

    return await health_check_service.get_live_status()


@router.get(
    "/ready",
    response_model=ReadyStatusResponse,
    responses={status.HTTP_400_BAD_REQUEST: {"model": ReadyStatusResponse}},
)
@ignore_transaction
@inject
async def get_ready_status(
    response: Response,
    health_check_service: HealthCheckService = HEALTH_CHECK_SERVICE_DEPEND,
) -> ReadyStatusResponse:
    """
    Endpoint for checking that all services what use the application are working correctly and application has access.
    """

    ready_status = await health_check_service.get_ready_status()

    if ready_status.status != HealthStatusEnum.healthy:
        response.status_code = status.HTTP_400_BAD_REQUEST

    return ready_status
