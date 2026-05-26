"""
Provider-agnostic embeddings factory. Switch via EMBEDDING_PROVIDER env var.
"""
from app.core.config import settings


def get_embeddings():
    match settings.embedding_provider:
        case "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.embedding_model,
                api_key=settings.openai_api_key,
            )
        case "local":
            # Uses sentence-transformers locally — no API key needed
            from langchain_community.embeddings import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        case _:
            raise ValueError(f"Unknown EMBEDDING_PROVIDER: {settings.embedding_provider!r}")
