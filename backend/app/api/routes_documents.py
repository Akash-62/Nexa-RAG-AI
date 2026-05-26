import logging
import uuid as uuid_module
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, DocumentStatus
from app.core.security import get_current_user_id
from app.schemas.documents import DocumentOut, DocumentListResponse, UploadResponse
from app.services.document_loader import save_upload
from app.services.ingestion import run_ingestion

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    # 1. Validate + save file to disk
    storage_path = await save_upload(file, user_id)
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()

    # 2. Create metadata record in PostgreSQL
    doc = Document(
        user_id=uuid_module.UUID(user_id),
        filename=file.filename,
        file_type=ext,
        storage_path=storage_path,
        status=DocumentStatus.pending,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 3. Queue ingestion as a background task (runs after response is sent)
    background_tasks.add_task(
        run_ingestion,
        document_id=str(doc.id),
        storage_path=storage_path,
        file_type=ext,
        user_id=user_id,
    )

    logger.info("Upload accepted: document=%s file=%s", doc.id, doc.filename)
    return UploadResponse(
        document_id=str(doc.id),
        filename=doc.filename,
        status=doc.status.value,
        message="Document accepted. Ingestion started in background.",
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == uuid_module.UUID(user_id))
        .order_by(Document.created_at.desc())
        .all()
    )
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == uuid_module.UUID(document_id),
        Document.user_id == uuid_module.UUID(user_id),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(
        Document.id == uuid_module.UUID(document_id),
        Document.user_id == uuid_module.UUID(user_id),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from app.services.vector_store import delete_document_vectors
    delete_document_vectors(str(doc.id))

    db.delete(doc)
    db.commit()
