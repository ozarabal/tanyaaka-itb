from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.models.schemas import ChatRequest, ChatResponse, Source
from app.services.rag_chain import rag_chain
from app.services.vector_store import vector_store_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not vector_store_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Vector store is empty. Please ingest documents first.",
        )

    try:
        result = await rag_chain.query(request.question)
    except Exception as e:
        logger.error("chat_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process question.")

    return ChatResponse(
        answer=result["answer"],
        sources=[Source(**s) for s in result["sources"]],
        model=result["model"],
    )
