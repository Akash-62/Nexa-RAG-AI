import logging
import uuid as uuid_module

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import UsageLog, AgentRun, ChatMessage, ChatSession
from app.core.security import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/usage")
def usage_summary(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    uid = uuid_module.UUID(user_id)

    # Aggregated token / cost stats from usage_logs
    token_row = db.query(
        func.coalesce(func.sum(UsageLog.tokens_in), 0).label("tokens_in"),
        func.coalesce(func.sum(UsageLog.tokens_out), 0).label("tokens_out"),
        func.coalesce(func.sum(UsageLog.estimated_cost), 0.0).label("cost"),
        func.count(UsageLog.id).label("calls"),
    ).filter(UsageLog.user_id == uid).one()

    # Agent run count
    agent_runs = (
        db.query(func.count(AgentRun.id))
        .filter(AgentRun.user_id == uid)
        .scalar() or 0
    )

    # Total messages (user + assistant) across all sessions
    messages = (
        db.query(func.count(ChatMessage.id))
        .join(ChatMessage.session)
        .filter(ChatSession.user_id == uid)
        .scalar() or 0
    )

    # Average RAG answer latency (assistant messages only)
    avg_latency = (
        db.query(func.avg(ChatMessage.latency_ms))
        .join(ChatMessage.session)
        .filter(ChatSession.user_id == uid, ChatMessage.role == "assistant")
        .scalar()
    )

    # Last 10 LLM operations for the activity feed
    recent_logs = (
        db.query(UsageLog)
        .filter(UsageLog.user_id == uid)
        .order_by(UsageLog.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_tokens_in": int(token_row.tokens_in),
        "total_tokens_out": int(token_row.tokens_out),
        "total_tokens": int(token_row.tokens_in) + int(token_row.tokens_out),
        "estimated_cost_usd": round(float(token_row.cost), 6),
        "total_calls": int(token_row.calls),
        "total_agent_runs": agent_runs,
        "total_messages": messages,
        "avg_latency_ms": round(float(avg_latency)) if avg_latency else 0,
        "recent_operations": [
            {
                "operation": r.operation,
                "model": r.model,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
                "cost_usd": round(r.estimated_cost, 6),
                "created_at": r.created_at.isoformat(),
            }
            for r in recent_logs
        ],
    }
