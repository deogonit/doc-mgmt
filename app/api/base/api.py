from fastapi import APIRouter

from app.api.base import health

api_base_router = APIRouter(prefix="")

api_base_router.include_router(router=health.router)
