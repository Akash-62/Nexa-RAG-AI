import re
import time
import logging
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Document, ChatSession, ChatMessage, Citation
from app.core.security import get_current_user_id
from app.schemas.chat import QueryRequest, QueryResponse, ChatSessionOut, CitationOut

logger = logging.getLogger(__name__)
router = APIRouter()

FALLBACK_ANSWER = (
    "I don't have enough context in the uploaded documents to answer this question. "
    "Try uploading more relevant documents or rephrasing your query."
)

# Matches single-word greetings with any amount of character elongation
# e.g. hi / hii / hiiii / hey / heyy / hello / helloo / yo / yoo
_GREETING_WORD_RE = re.compile(
    r"^(hi+|hey+|hello+|howdy+|sup+|yo+|greetings+|hola+|namaste+)$",
    re.IGNORECASE,
)

_GREETING_PHRASES = {
    "good morning", "good afternoon", "good evening", "good night",
    "how are you", "how r u", "how are u", "what's up", "whats up",
    "how do you do", "nice to meet you",
}

SMALLTALK_PROMPT = """\
You are Nexa — a sharp, confident AI built for document intelligence.
The user just said something casual. Reply naturally in 1-2 sentences max.
Sound warm and human. Drop one punchy line about what you can do if it fits.
No corporate-speak. No "I am an AI". Just vibe with them and stay impressive.

User: {message}
Nexa:"""

RAG_PROMPT = """\
You are Nexa — sharp, confident, and direct. Answer using ONLY the context below.

Tone rules:
- Sound like a knowledgeable human, not a robot. Be conversational but precise.
- Keep answers short and punchy. No fluff, no filler phrases.
- For multi-part questions, answer each part you find — briefly note any gaps.
- Never start with "Based on the context" or "According to the document" — just answer.
- Only say "I don't have enough context in the uploaded documents to answer this." \
if the context is completely unrelated to the question.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


# ─── Main RAG endpoint ─────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
def query(
    payload: QueryRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    t_start = time.time()

    # 0. Small-talk / greeting shortcut — skip RAG entirely
    _clean = payload.query.strip().lower().rstrip("!?.")
    _words = _clean.split()
    _is_greeting = bool(_words) and len(_words) <= 5 and (
        bool(_GREETING_WORD_RE.match(_words[0]))
        or _clean in _GREETING_PHRASES
    )
    if _is_greeting:
        from app.services.llm_client import get_llm
        session = _get_or_create_session(db, user_id, payload.session_id, payload.query)
        db.add(ChatMessage(session_id=session.id, role="user", content=payload.query))
        db.commit()
        llm = get_llm(temperature=0.7)
        resp = llm.invoke(SMALLTALK_PROMPT.format(message=payload.query))
        answer = resp.content if hasattr(resp, "content") else str(resp)
        latency_ms = int((time.time() - t_start) * 1000)
        db.add(ChatMessage(session_id=session.id, role="assistant", content=answer, latency_ms=latency_ms, confidence_score=1.0))
        db.commit()
        _log_usage(db, user_id, payload.query, answer)
        return QueryResponse(answer=answer, citations=[], confidence_score=1.0, latency_ms=latency_ms, session_id=str(session.id))

    # 1. Retrieve relevant chunks from ChromaDB
    from app.services.retrieval import retrieve_chunks
    chunks = retrieve_chunks(
        query=payload.query,
        document_ids=payload.document_ids,
        top_k=8,
    )

    # 2. Compute confidence
    from app.services.confidence import compute_confidence, is_low_confidence
    confidence = compute_confidence(chunks)

    # 3. Get or create chat session
    session = _get_or_create_session(db, user_id, payload.session_id, payload.query)

    # 4. Persist the user turn
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=payload.query,
    )
    db.add(user_msg)
    db.commit()

    # 5. Low-confidence path — refuse rather than hallucinate
    if not chunks or is_low_confidence(confidence):
        latency_ms = int((time.time() - t_start) * 1000)
        assistant_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=FALLBACK_ANSWER,
            latency_ms=latency_ms,
            confidence_score=confidence,
        )
        db.add(assistant_msg)
        db.commit()
        return QueryResponse(
            answer=FALLBACK_ANSWER,
            citations=[],
            confidence_score=confidence,
            latency_ms=latency_ms,
            session_id=str(session.id),
        )

    # 6. Format context + call LLM
    from app.services.citation_builder import format_context_block, build_citations
    from app.services.llm_client import get_llm

    context = format_context_block(chunks)
    prompt = RAG_PROMPT.format(context=context, question=payload.query)
    llm = get_llm(temperature=0.0)
    response = llm.invoke(prompt)
    answer: str = response.content if hasattr(response, "content") else str(response)

    # 7. Build citation objects (resolve filenames from DB)
    doc_ids = list({c["metadata"].get("document_id", "") for c in chunks})
    doc_map = _get_doc_filename_map(db, doc_ids, user_id)
    citations: list[CitationOut] = build_citations(chunks, doc_map)

    latency_ms = int((time.time() - t_start) * 1000)

    # 8. Persist assistant message + citations
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer,
        latency_ms=latency_ms,
        confidence_score=confidence,
    )
    db.add(assistant_msg)
    db.flush()  # populate assistant_msg.id before inserting citations

    for cit in citations:
        db.add(Citation(
            message_id=assistant_msg.id,
            document_id=uuid_module.UUID(str(cit.document_id)),
            chunk_index=cit.chunk_index,
            page_number=cit.page_number,
            text_excerpt=cit.text_excerpt,
            relevance_score=cit.relevance_score,
        ))

    db.commit()

    # 9. Log token usage
    _log_usage(db, user_id, prompt, answer)

    logger.info(
        "RAG query done: session=%s chunks=%d confidence=%.2f latency=%dms",
        session.id, len(chunks), confidence, latency_ms,
    )
    return QueryResponse(
        answer=answer,
        citations=citations,
        confidence_score=confidence,
        latency_ms=latency_ms,
        session_id=str(session.id),
    )


# ─── Sessions ──────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[ChatSessionOut])
def list_sessions(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == uuid_module.UUID(user_id))
        .order_by(ChatSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == uuid_module.UUID(session_id),
        ChatSession.user_id == uuid_module.UUID(user_id),
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "confidence_score": m.confidence_score,
            "latency_ms": m.latency_ms,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_create_session(
    db: Session,
    user_id: str,
    session_id: str | None,
    first_query: str,
) -> ChatSession:
    if session_id:
        existing = db.query(ChatSession).filter(
            ChatSession.id == uuid_module.UUID(session_id),
            ChatSession.user_id == uuid_module.UUID(user_id),
        ).first()
        if existing:
            return existing

    title = first_query[:60] + ("…" if len(first_query) > 60 else "")
    session = ChatSession(user_id=uuid_module.UUID(user_id), title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_doc_filename_map(db: Session, doc_ids: list[str], user_id: str) -> dict[str, str]:
    valid_ids = [uuid_module.UUID(d) for d in doc_ids if d]
    if not valid_ids:
        return {}
    docs = db.query(Document).filter(
        Document.id.in_(valid_ids),
        Document.user_id == uuid_module.UUID(user_id),
    ).all()
    return {str(d.id): d.filename for d in docs}


def _log_usage(db: Session, user_id: str, prompt: str, answer: str) -> None:
    try:
        from app.services.metrics import log_usage
        from app.core.config import settings
        tokens_in = len(prompt) // 4   # rough 4-chars-per-token estimate
        tokens_out = len(answer) // 4
        log_usage(db, user_id, settings.llm_model, tokens_in, tokens_out, "rag_query")
    except Exception as e:
        db.rollback()  # restore session — metrics failure must not poison the main transaction
        logger.warning("Usage logging failed: %s", e)
