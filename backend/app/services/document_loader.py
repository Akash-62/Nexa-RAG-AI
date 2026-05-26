import logging
from pathlib import Path

from fastapi import UploadFile, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_upload(file: UploadFile, user_id: str) -> str:
    """Validate size + extension, write to disk, return absolute storage path."""
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type .{ext}. Allowed: {settings.allowed_extensions}")

    content = await file.read()
    if len(content) > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_file_size_mb} MB limit")
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")

    dest = Path(settings.upload_dir) / user_id
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / (file.filename or f"upload.{ext}")
    path.write_bytes(content)
    logger.debug("Saved upload to %s (%d bytes)", path, len(content))
    return str(path)


def extract_text(storage_path: str, file_type: str) -> list[dict]:
    """
    Extract text from a stored file.
    Returns list of {page_number: int, text: str} dicts.
    """
    path = Path(storage_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {storage_path}")

    match file_type.lower():
        case "pdf":
            return _extract_pdf(path)
        case "docx":
            return _extract_docx(path)
        case "txt":
            return _extract_txt(path)
        case _:
            raise ValueError(f"Cannot extract text from .{file_type}")


def _extract_pdf(path: Path) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Install pypdf: pip install pypdf")

    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append({"page_number": i, "text": text})
    if not pages:
        logger.warning("PDF %s yielded no extractable text", path.name)
    return pages


def _extract_docx(path: Path) -> list[dict]:
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ImportError("Install python-docx: pip install python-docx")

    doc = DocxDocument(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        logger.warning("DOCX %s yielded no extractable text", path.name)
        return []
    # DOCX has no page concept — treat whole file as page 1
    return [{"page_number": 1, "text": "\n\n".join(paragraphs)}]


def _extract_txt(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        logger.warning("TXT %s is empty", path.name)
        return []
    return [{"page_number": 1, "text": text}]
