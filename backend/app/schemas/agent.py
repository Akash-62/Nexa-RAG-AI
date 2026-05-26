from pydantic import BaseModel
from typing import Literal


class AgentRunRequest(BaseModel):
    task_type: Literal["summarize", "compare", "extract_actions", "generate_email"]
    document_ids: list[str]
    query: str | None = None       # optional extra context for email/actions
    email_context: str | None = None


class ActionItem(BaseModel):
    task: str
    owner: str | None
    deadline: str | None
    priority: str | None
    status: str = "pending"


class AgentRunResponse(BaseModel):
    run_id: str
    task_type: str
    status: str
    output: dict                   # task-specific output blob
    latency_ms: int
