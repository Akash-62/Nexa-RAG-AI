from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.db.session import engine
from app.db import models
from app.api import routes_auth, routes_documents, routes_chat, routes_agent, routes_metrics
from app.middleware.request_logger import RequestLoggerMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("DEBUG" if settings.debug else "INFO")
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    models.Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise RAG Agent Platform — document intelligence and workflow automation.",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/auth", tags=["auth"])
app.include_router(routes_documents.router, prefix="/documents", tags=["documents"])
app.include_router(routes_chat.router, prefix="/chat", tags=["chat"])
app.include_router(routes_agent.router, prefix="/agent", tags=["agent"])
app.include_router(routes_metrics.router, prefix="/metrics", tags=["metrics"])


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "version": settings.app_version}
