from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.models.schemas import (
    DocumentInfo,
    DocumentListResponse,
    IngestRequest,
    IngestResponse,
)
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import vector_store_service

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/documents")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_documents(request: IngestRequest = IngestRequest()):
    """Ingest PDFs from the configured directory into the vector store."""
    try:
        processor = DocumentProcessor()
        chunks = processor.process_directory(request.directory)

        if not chunks:
            raise HTTPException(status_code=404, detail="No PDF documents found.")

        count = vector_store_service.add_documents(chunks)
        doc_names = {c.metadata.get("source_filename", "") for c in chunks}

        return IngestResponse(
            status="completed",
            documents_processed=len(doc_names),
            chunks_created=count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("ingest_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("", response_model=DocumentListResponse)
async def list_documents():
    """List all ingested documents and their chunk counts."""
    doc_counts = vector_store_service.list_documents()
    documents = [
        DocumentInfo(filename=fname, num_chunks=count)
        for fname, count in doc_counts.items()
    ]
    return DocumentListResponse(
        documents=documents,
        total_chunks=sum(d.num_chunks for d in documents),
    )
