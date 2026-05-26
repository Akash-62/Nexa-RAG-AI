"""
Block 5 agent workflow tests.
The LangGraph graph (run_agent) is fully mocked; only the HTTP layer and DB
persistence are exercised against the SQLite test database.
"""
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient

REGISTER_URL = "/auth/register"
RUN_URL = "/agent/run"
RUNS_URL = "/agent/runs"

DOC_ID = str(uuid.uuid4())


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _token(client: TestClient, email: str = "agent_user@example.com") -> str:
    r = client.post(REGISTER_URL, json={"name": "Agent User", "email": email, "password": "pass1234"})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _run(client, token, task_type, output, **extra):
    payload = {"task_type": task_type, "document_ids": [DOC_ID], **extra}
    with patch("app.services.agent_graph.run_agent", return_value=output):
        return client.post(RUN_URL, json=payload, headers=_auth(token))


# ─── Auth guard ─────────────────────────────────────────────────────────────────

def test_run_without_auth_returns_401(client: TestClient):
    r = client.post(RUN_URL, json={"task_type": "summarize", "document_ids": [DOC_ID]})
    assert r.status_code == 401


def test_list_runs_without_auth_returns_401(client: TestClient):
    r = client.get(RUNS_URL)
    assert r.status_code == 401


# ─── Input validation ───────────────────────────────────────────────────────────

def test_run_missing_document_ids_returns_422(client: TestClient):
    token = _token(client, "av1@example.com")
    r = client.post(
        RUN_URL,
        json={"task_type": "summarize", "document_ids": []},
        headers=_auth(token),
    )
    assert r.status_code == 422


def test_run_invalid_task_type_returns_422(client: TestClient):
    token = _token(client, "av2@example.com")
    r = client.post(
        RUN_URL,
        json={"task_type": "invalid_task", "document_ids": [DOC_ID]},
        headers=_auth(token),
    )
    assert r.status_code == 422


# ─── Summarize ──────────────────────────────────────────────────────────────────

def test_summarize_returns_summary(client: TestClient):
    token = _token(client, "a1@example.com")
    output = {"summary": "This document covers quarterly financials."}
    r = _run(client, token, "summarize", output)
    assert r.status_code == 200
    data = r.json()
    assert data["task_type"] == "summarize"
    assert data["status"] == "completed"
    assert data["output"]["summary"] == output["summary"]
    assert "run_id" in data
    assert data["latency_ms"] >= 0


# ─── Compare ────────────────────────────────────────────────────────────────────

def test_compare_returns_comparison(client: TestClient):
    token = _token(client, "a2@example.com")
    output = {"comparison": "Document A focuses on revenue; Document B on costs."}
    r = _run(client, token, "compare", output, query="How do they differ?")
    assert r.status_code == 200
    data = r.json()
    assert data["task_type"] == "compare"
    assert data["status"] == "completed"
    assert "comparison" in data["output"]


# ─── Extract actions ────────────────────────────────────────────────────────────

def test_extract_actions_returns_action_items(client: TestClient):
    token = _token(client, "a3@example.com")
    output = {
        "action_items": [
            {"task": "Send report", "owner": "Alice", "deadline": "2024-02-01",
             "priority": "high", "status": "pending"},
        ]
    }
    r = _run(client, token, "extract_actions", output)
    assert r.status_code == 200
    data = r.json()
    assert data["task_type"] == "extract_actions"
    items = data["output"]["action_items"]
    assert len(items) == 1
    assert items[0]["task"] == "Send report"
    assert items[0]["priority"] == "high"


# ─── Generate email ─────────────────────────────────────────────────────────────

def test_generate_email_returns_email(client: TestClient):
    token = _token(client, "a4@example.com")
    output = {"email": "Subject: Q4 Update\n\nDear Team,\n\nPlease review the attached report.\n\nBest regards"}
    r = _run(client, token, "generate_email", output,
             email_context="Send a summary to stakeholders",
             query="Q4 financials")
    assert r.status_code == 200
    data = r.json()
    assert data["task_type"] == "generate_email"
    assert "email" in data["output"]


# ─── DB persistence ─────────────────────────────────────────────────────────────

def test_run_is_persisted_and_appears_in_list(client: TestClient):
    token = _token(client, "a5@example.com")
    output = {"summary": "Persisted summary."}
    _run(client, token, "summarize", output)

    r = client.get(RUNS_URL, headers=_auth(token))
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) >= 1
    assert runs[0]["task_type"] == "summarize"
    assert runs[0]["status"] == "completed"


def test_runs_scoped_to_user(client: TestClient):
    """User B cannot see User A's agent runs."""
    token_a = _token(client, "agA@example.com")
    token_b = _token(client, "agB@example.com")
    output = {"summary": "Only for A."}
    _run(client, token_a, "summarize", output)

    r = client.get(RUNS_URL, headers=_auth(token_b))
    assert r.json() == []


def test_failed_run_is_persisted_as_failed(client: TestClient):
    token = _token(client, "a6@example.com")
    with patch("app.services.agent_graph.run_agent", side_effect=RuntimeError("graph error")):
        r = client.post(
            RUN_URL,
            json={"task_type": "summarize", "document_ids": [DOC_ID]},
            headers=_auth(token),
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "failed"
    assert "error" in data["output"]

    runs = client.get(RUNS_URL, headers=_auth(token)).json()
    assert runs[0]["status"] == "failed"


def test_list_runs_empty_for_new_user(client: TestClient):
    token = _token(client, "a7@example.com")
    r = client.get(RUNS_URL, headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == []


# ─── Agent graph unit tests (no LLM, no DB) ────────────────────────────────────

def test_extract_actions_parses_json_from_llm():
    from app.services.agent_graph import _extract_actions, AgentState

    llm_output = '[{"task": "Write report", "owner": "Bob", "deadline": null, "priority": "medium", "status": "pending"}]'
    state: AgentState = {
        "task_type": "extract_actions",
        "document_ids": [],
        "query": None,
        "email_context": None,
        "chunks": [{"text": "Bob will write the report.", "metadata": {"page_number": 1, "filename": "notes.txt"}}],
        "output": {},
        "error": None,
    }
    with patch("app.services.agent_graph._llm_text", return_value=llm_output):
        result = _extract_actions(state)

    items = result["output"]["action_items"]
    assert len(items) == 1
    assert items[0]["task"] == "Write report"
    assert items[0]["owner"] == "Bob"


def test_extract_actions_handles_invalid_json():
    from app.services.agent_graph import _extract_actions, AgentState

    state: AgentState = {
        "task_type": "extract_actions",
        "document_ids": [],
        "query": None,
        "email_context": None,
        "chunks": [{"text": "Some text.", "metadata": {"page_number": 1}}],
        "output": {},
        "error": None,
    }
    with patch("app.services.agent_graph._llm_text", return_value="not valid json at all"):
        result = _extract_actions(state)

    assert result["output"]["action_items"] == []


def test_summarize_node_returns_summary():
    from app.services.agent_graph import _summarize, AgentState

    state: AgentState = {
        "task_type": "summarize",
        "document_ids": [],
        "query": None,
        "email_context": None,
        "chunks": [{"text": "Key findings are...", "metadata": {"page_number": 1, "filename": "doc.pdf"}}],
        "output": {},
        "error": None,
    }
    with patch("app.services.agent_graph._llm_text", return_value="A concise summary."):
        result = _summarize(state)

    assert result["output"]["summary"] == "A concise summary."


def test_summarize_node_no_chunks_returns_fallback():
    from app.services.agent_graph import _summarize, AgentState

    state: AgentState = {
        "task_type": "summarize",
        "document_ids": [],
        "query": None,
        "email_context": None,
        "chunks": [],
        "output": {},
        "error": None,
    }
    result = _summarize(state)
    assert "No content found" in result["output"]["summary"]
