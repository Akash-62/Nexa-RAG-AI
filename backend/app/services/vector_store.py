"""
ChromaDB client. All vector read/write operations go through this module.
chromadb is imported lazily so the module loads without it in test environments.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_chroma_client():
    global _client
    if _client is None:
        import chromadb
        if settings.chroma_mode == "http":
            _client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        else:
            import os
            os.makedirs(settings.chroma_persist_dir, exist_ok=True)
            _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def get_vector_store():
    """Returns a LangChain-compatible Chroma vector store."""
    from langchain_chroma import Chroma
    from app.services.embeddings import get_embeddings
    return Chroma(
        client=get_chroma_client(),
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(),
    )


def add_chunks(chunks: list[dict]) -> list[str]:
    """
    Embed and store text chunks in ChromaDB.
    Returns list of vector IDs (one per chunk).
    """
    if not chunks:
        return []

    store = get_vector_store()
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "document_id": str(c["document_id"]),
            "user_id": str(c["user_id"]),
            "chunk_index": c["chunk_index"],
            "page_number": c.get("page_number") or 0,
            "char_count": c.get("char_count", 0),
        }
        for c in chunks
    ]
    ids = [f"{c['document_id']}_{c['chunk_index']}" for c in chunks]

    store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    logger.info("Stored %d chunks (document %s)", len(ids), chunks[0]["document_id"])
    return ids


def delete_document_vectors(document_id: str) -> None:
    """Remove all vectors for a document from ChromaDB."""
    try:
        client = get_chroma_client()
        collection = client.get_or_create_collection(settings.chroma_collection)
        results = collection.get(where={"document_id": str(document_id)})
        if results["ids"]:
            collection.delete(ids=results["ids"])
            logger.info("Deleted %d vectors for document %s", len(results["ids"]), document_id)
    except Exception as e:
        logger.warning("Could not delete vectors for %s: %s", document_id, e)


def similarity_search(query: str, document_ids: list[str] | None = None, top_k: int = 5) -> list[dict]:
    """
    Search ChromaDB for top-k chunks matching the query.
    Returns list of {text, metadata, score} dicts.
    """
    store = get_vector_store()
    where_filter = None
    if document_ids:
        where_filter = {"document_id": {"$in": [str(d) for d in document_ids]}}

    results = store.similarity_search_with_relevance_scores(
        query=query,
        k=top_k,
        filter=where_filter,
    )
    return [
        {"text": doc.page_content, "metadata": doc.metadata, "score": (score + 1) / 2}
        for doc, score in results
    ]
