"""
Builds structured citations from retrieved chunks and formats context for the LLM.
"""
from app.schemas.chat import CitationOut


def build_citations(chunks: list[dict], doc_filename_map: dict[str, str]) -> list[CitationOut]:
    """
    Maps retrieval results → CitationOut objects.

    doc_filename_map: {str(document_id): filename}
    """
    seen_ids: set[str] = set()
    citations: list[CitationOut] = []

    for chunk in chunks:
        meta = chunk.get("metadata", {})
        doc_id = str(meta.get("document_id", ""))
        chunk_index = int(meta.get("chunk_index", 0))
        dedup_key = f"{doc_id}_{chunk_index}"
        if dedup_key in seen_ids:
            continue
        seen_ids.add(dedup_key)

        citations.append(CitationOut(
            document_id=doc_id,
            filename=doc_filename_map.get(doc_id, "Unknown Document"),
            page_number=meta.get("page_number") or None,
            chunk_index=chunk_index,
            text_excerpt=chunk.get("text", "")[:300],
            relevance_score=round(float(chunk.get("score", 0.0)), 4),
        ))

    return citations


def format_context_block(chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a numbered context block for the LLM prompt.
    Each source is labelled with its page number so the model can reference it.
    """
    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.get("metadata", {})
        page = meta.get("page_number") or "?"
        filename = meta.get("filename", "")
        header = f"[Source {i}]" + (f" {filename}" if filename else "") + f" — Page {page}"
        parts.append(f"{header}:\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)
