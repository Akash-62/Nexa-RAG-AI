from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class CitationOut(BaseModel):
    document_id: UUID
    filename: str
    page_number: int | None
    chunk_index: int
    text_excerpt: str
    relevance_score: float


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None
    document_ids: list[str] | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    confidence_score: float
    latency_ms: int
    session_id: str


class ChatSessionOut(BaseModel):
    id: UUID
    title: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
