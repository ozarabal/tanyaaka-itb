from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        examples=["Apa syarat kelulusan di ITB?"],
    )


class Source(BaseModel):
    document: str
    page: Optional[int] = None
    content_snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    model: str


class IngestRequest(BaseModel):
    directory: Optional[str] = None


class IngestResponse(BaseModel):
    status: str
    documents_processed: int
    chunks_created: int


class DocumentInfo(BaseModel):
    filename: str
    num_chunks: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_chunks: int


class HealthResponse(BaseModel):
    status: str
    version: str
    vector_store_ready: bool
