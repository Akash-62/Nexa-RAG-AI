import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Text, Enum as SAEnum, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ─── Enums ─────────────────────────────────────────────────────────────────────

class DocumentStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class AgentTaskType(str, enum.Enum):
    qa = "qa"
    summarize = "summarize"
    compare = "compare"
    extract_actions = "extract_actions"
    generate_email = "generate_email"


# ─── Tables ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_type = Column(String(50), nullable=False)
    storage_path = Column(String(1024), nullable=False)
    status = Column(SAEnum(DocumentStatus), default=DocumentStatus.pending, nullable=False)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text_preview = Column(Text)
    vector_id = Column(String(255))
    page_number = Column(Integer)
    char_count = Column(Integer)
    metadata_ = Column("metadata", JSON, default=dict)

    document = relationship("Document", back_populates="chunks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(512))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    latency_ms = Column(Integer)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    session = relationship("ChatSession", back_populates="messages")
    citations = relationship("Citation", back_populates="message", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(Uuid(as_uuid=True), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer)
    page_number = Column(Integer)
    text_excerpt = Column(Text)
    relevance_score = Column(Float)

    message = relationship("ChatMessage", back_populates="citations")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(SAEnum(AgentTaskType), nullable=False)
    input_json = Column(JSON)
    output_json = Column(JSON)
    status = Column(String(50), default="pending")
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model = Column(String(255))
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    operation = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
