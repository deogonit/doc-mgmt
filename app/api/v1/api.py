from fastapi import APIRouter

from app.api.v1.doc_generation import doc_generation
from app.api.v1.esign import esign, webhook

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(router=doc_generation.router)
api_v1_router.include_router(router=esign.router)
api_v1_router.include_router(router=webhook.router)
