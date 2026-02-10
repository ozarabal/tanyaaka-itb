from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse
from app.services.vector_store import vector_store_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        vector_store_ready=vector_store_service.is_ready,
    )
