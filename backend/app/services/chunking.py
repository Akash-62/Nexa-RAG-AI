import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def chunk_pages(pages: list[dict], document_id: str, user_id: str) -> list[dict]:
    """
    Split extracted pages into overlapping text chunks.

    Input:  pages = [{page_number: int, text: str}, ...]
    Output: chunks = [{text, document_id, user_id, chunk_index, page_number, char_count}, ...]
    """
    splitter = _build_splitter()
    chunks: list[dict] = []

    for page in pages:
        page_text = page.get("text", "").strip()
        if not page_text:
            continue
        splits = splitter(page_text)
        for split_text in splits:
            split_text = split_text.strip()
            if not split_text:
                continue
            chunks.append({
                "text": split_text,
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": len(chunks),
                "page_number": page["page_number"],
                "char_count": len(split_text),
            })

    logger.debug("Chunked document %s → %d chunks", document_id, len(chunks))
    return chunks


def _build_splitter():
    """Returns a callable that splits a string into chunks."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        return splitter.split_text
    except ImportError:
        # Lightweight fallback for test environments without langchain
        return _simple_splitter(settings.chunk_size, settings.chunk_overlap)


def _simple_splitter(chunk_size: int, overlap: int):
    def split(text: str) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return chunks
    return split
