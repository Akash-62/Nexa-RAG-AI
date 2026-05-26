import time
import logging
import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import AgentRun, AgentTaskType
from app.core.security import get_current_user_id
from app.schemas.agent import AgentRunRequest, AgentRunResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/run", response_model=AgentRunResponse)
def run_agent_endpoint(
    payload: AgentRunRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not payload.document_ids:
        raise HTTPException(status_code=422, detail="At least one document_id is required")

    t_start = time.time()

    # Persist the run record upfront so we always have a run_id to return
    run = AgentRun(
        user_id=uuid_module.UUID(user_id),
        task_type=AgentTaskType(payload.task_type),
        input_json={
            "document_ids": payload.document_ids,
            "query": payload.query,
            "email_context": payload.email_context,
        },
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        from app.services.agent_graph import run_agent
        output = run_agent(
            task_type=payload.task_type,
            document_ids=payload.document_ids,
            query=payload.query,
            email_context=payload.email_context,
        )
        status = "completed"
    except Exception as exc:
        logger.exception("Agent run %s failed: %s", run.id, exc)
        output = {"error": str(exc)}
        status = "failed"

    latency_ms = int((time.time() - t_start) * 1000)

    run.output_json = output
    run.status = status
    run.latency_ms = latency_ms
    db.commit()

    logger.info(
        "Agent run done: id=%s task=%s status=%s latency=%dms",
        run.id, payload.task_type, status, latency_ms,
    )

    return AgentRunResponse(
        run_id=str(run.id),
        task_type=payload.task_type,
        status=status,
        output=output,
        latency_ms=latency_ms,
    )


@router.get("/runs", response_model=list[AgentRunResponse])
def list_runs(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.user_id == uuid_module.UUID(user_id))
        .order_by(AgentRun.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        AgentRunResponse(
            run_id=str(r.id),
            task_type=r.task_type.value,
            status=r.status,
            output=r.output_json or {},
            latency_ms=r.latency_ms or 0,
        )
        for r in runs
    ]
