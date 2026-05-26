"""
Logs token usage and estimated cost to the usage_logs table.
"""
import logging
import uuid as uuid_module
from sqlalchemy.orm import Session
from app.db.models import UsageLog

logger = logging.getLogger(__name__)

# Rough cost per 1k tokens (update as model pricing changes)
COST_PER_1K = {
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "claude-3-5-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "gemini-1.5-flash": 0.000075,
}


def log_usage(
    db: Session,
    user_id: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    operation: str,
) -> None:
    rate = COST_PER_1K.get(model, 0.001)
    cost = ((tokens_in + tokens_out) / 1000) * rate

    record = UsageLog(
        user_id=uuid_module.UUID(user_id),
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        estimated_cost=cost,
        operation=operation,
    )
    db.add(record)
    db.commit()
    logger.debug("Usage logged: %s tokens=%d+%d cost=$%.5f", operation, tokens_in, tokens_out, cost)
