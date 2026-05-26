"""
Converts a user query into an embedding and retrieves top-k chunks from ChromaDB.
Thin wrapper around vector_store.similarity_search that adds score filtering.
"""
import logging
from app.services.vector_store import similarity_search

logger = logging.getLogger(__name__)

MIN_SCORE = 0.20  # discard chunks below this relevance — pure noise


def retrieve_chunks(
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Returns list of {text, metadata, score} dicts sorted by score descending.
    Filters out chunks below MIN_SCORE.
    """
    raw = similarity_search(query=query, document_ids=document_ids, top_k=top_k)
    filtered = [r for r in raw if r.get("score", 0.0) >= MIN_SCORE]
    filtered.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    logger.debug("Retrieved %d/%d chunks for query: %r", len(filtered), len(raw), query[:60])
    return filtered
