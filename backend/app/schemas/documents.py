from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    file_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    message: str
