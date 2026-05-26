from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Annotated
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Nexa RAG Agent Platform"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://nexarag:nexarag_dev@localhost:5432/nexarag"

    # JWT
    secret_key: str = "change-me-generate-a-real-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # CORS — stored as JSON string in env, e.g. '["http://localhost:3000"]'
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    # LLM
    llm_provider: str = "openai"   # openai | anthropic | gemini | groq
    llm_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""

    # Embeddings
    embedding_provider: str = "openai"  # openai | local
    embedding_model: str = "text-embedding-3-small"

    # ChromaDB — set CHROMA_MODE=http to use an external HTTP server (local Docker)
    # Leave unset (or "persistent") for embedded mode used in production deployments
    chroma_mode: str = "persistent"          # "persistent" | "http"
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "documents"
    chroma_persist_dir: str = "/data/chroma"

    # File upload
    upload_dir: str = "uploads"
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "docx", "txt"]

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200


settings = Settings()
