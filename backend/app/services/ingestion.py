"""
Orchestrates the full document ingestion pipeline as a background task.

Flow: save → extract text → chunk → embed + store vectors → save chunks to DB → mark ready
"""
import logging
import uuid as uuid_module

from app.db.session import SessionLocal
from app.db.models import Document, DocumentChunk, DocumentStatus
from app.services.document_loader import extract_text
from app.services.chunking import chunk_pages
from app.services.vector_store import add_chunks, delete_document_vectors

logger = logging.getLogger(__name__)


def run_ingestion(document_id: str, storage_path: str, file_type: str, user_id: str) -> None:
    """
    Runs synchronously as a FastAPI BackgroundTask.
    Creates its own DB session (request session is closed by this point).
    """
    db = SessionLocal()
    doc = None
    try:
        doc_uuid = uuid_module.UUID(document_id)
        doc = db.query(Document).filter(Document.id == doc_uuid).first()
        if not doc:
            logger.error("Ingestion: document %s not found in DB", document_id)
            return

        # Mark as processing
        doc.status = DocumentStatus.processing
        db.commit()

        # 1. Extract text pages from file
        pages = extract_text(storage_path, file_type)
        if not pages:
            raise ValueError("No text could be extracted from the document")

        # 2. Split pages into overlapping chunks
        chunks = chunk_pages(pages, document_id, user_id)
        if not chunks:
            raise ValueError("Document produced zero chunks after splitting")

        # 3. Embed chunks and store in ChromaDB
        vector_ids = add_chunks(chunks)

        # 4. Persist chunk metadata to PostgreSQL
        for chunk, vector_id in zip(chunks, vector_ids):
            db.add(DocumentChunk(
                document_id=doc_uuid,
                chunk_index=chunk["chunk_index"],
                text_preview=chunk["text"][:200],
                vector_id=vector_id,
                page_number=chunk.get("page_number"),
                char_count=chunk.get("char_count", 0),
                metadata_={"page_number": chunk.get("page_number")},
            ))

        # 5. Mark document as ready
        doc.status = DocumentStatus.ready
        doc.chunk_count = len(chunks)
        db.commit()
        logger.info("Ingestion complete: document=%s chunks=%d", document_id, len(chunks))

    except Exception as exc:
        logger.error("Ingestion failed for document %s: %s", document_id, exc, exc_info=True)
        if doc is not None:
            try:
                doc.status = DocumentStatus.failed
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()
