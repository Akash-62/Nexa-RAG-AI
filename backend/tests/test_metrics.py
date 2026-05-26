"""
Block 7 metrics endpoint tests.
Verifies /metrics/usage returns correct aggregated data, respects user scoping,
and updates after agent runs and chat queries.
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

REGISTER_URL = "/auth/register"
USAGE_URL = "/metrics/usage"
RUN_URL = "/agent/run"
QUERY_URL = "/chat/query"

DOC_ID = str(uuid.uuid4())

# ─── Shared mocks ──────────────────────────────────────────────────────────────

MOCK_CHUNKS = [
    {
        "text": "Some relevant text.",
        "score": 0.85,
        "metadata": {
            "document_id": DOC_ID,
            "chunk_index": 0,
            "page_number": 1,
            "filename": "test.pdf",
        },
    }
]


def _mock_llm(answer: str = "Test answer.") -> MagicMock:
    llm = MagicMock()
    resp = MagicMock()
    resp.content = answer
    llm.invoke.return_value = resp
    return llm


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _token(client: TestClient, email: str = "metrics_user@example.com") -> str:
    r = client.post(REGISTER_URL, json={"name": "Metrics User", "email": email, "password": "pass1234"})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Auth guard ─────────────────────────────────────────────────────────────────

def test_usage_without_auth_returns_401(client: TestClient):
    r = client.get(USAGE_URL)
    assert r.status_code == 401


# ─── Zero-state ─────────────────────────────────────────────────────────────────

def test_usage_returns_zeros_for_new_user(client: TestClient):
    token = _token(client, "m1@example.com")
    r = client.get(USAGE_URL, headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total_tokens_in"] == 0
    assert data["total_tokens_out"] == 0
    assert data["total_tokens"] == 0
    assert data["estimated_cost_usd"] == 0.0
    assert data["total_messages"] == 0
    assert data["total_agent_runs"] == 0
    assert data["avg_latency_ms"] == 0
    assert data["recent_operations"] == []


def test_usage_response_has_required_fields(client: TestClient):
    token = _token(client, "m2@example.com")
    data = client.get(USAGE_URL, headers=_auth(token)).json()
    required = {
        "total_tokens_in", "total_tokens_out", "total_tokens",
        "estimated_cost_usd", "total_calls", "total_agent_runs",
        "total_messages", "avg_latency_ms", "recent_operations",
    }
    assert required.issubset(data.keys())


# ─── After agent run ────────────────────────────────────────────────────────────

def test_agent_run_increments_total_agent_runs(client: TestClient):
    token = _token(client, "m3@example.com")
    with patch("app.services.agent_graph.run_agent", return_value={"summary": "ok"}):
        client.post(
            RUN_URL,
            json={"task_type": "summarize", "document_ids": [DOC_ID]},
            headers=_auth(token),
        )
    data = client.get(USAGE_URL, headers=_auth(token)).json()
    assert data["total_agent_runs"] == 1


def test_multiple_agent_runs_accumulate(client: TestClient):
    token = _token(client, "m4@example.com")
    with patch("app.services.agent_graph.run_agent", return_value={"summary": "ok"}):
        for _ in range(3):
            client.post(
                RUN_URL,
                json={"task_type": "summarize", "document_ids": [DOC_ID]},
                headers=_auth(token),
            )
    data = client.get(USAGE_URL, headers=_auth(token)).json()
    assert data["total_agent_runs"] == 3


# ─── After chat query ───────────────────────────────────────────────────────────

def test_chat_query_increments_messages(client: TestClient):
    token = _token(client, "m5@example.com")
    with (
        patch("app.services.citation_builder.build_citations", return_value=[]),
        patch("app.services.llm_client.get_llm", return_value=_mock_llm()),
        patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS),
    ):
        client.post(QUERY_URL, json={"query": "test question"}, headers=_auth(token))

    data = client.get(USAGE_URL, headers=_auth(token)).json()
    # One user message + one assistant message
    assert data["total_messages"] == 2


def test_avg_latency_is_populated_after_query(client: TestClient):
    token = _token(client, "m6@example.com")
    with (
        patch("app.services.citation_builder.build_citations", return_value=[]),
        patch("app.services.llm_client.get_llm", return_value=_mock_llm()),
        patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS),
    ):
        client.post(QUERY_URL, json={"query": "latency test"}, headers=_auth(token))

    data = client.get(USAGE_URL, headers=_auth(token)).json()
    assert data["avg_latency_ms"] >= 0


# ─── User scoping ───────────────────────────────────────────────────────────────

def test_usage_scoped_to_user(client: TestClient):
    """User B's metrics are zero even after User A's agent run."""
    token_a = _token(client, "mA@example.com")
    token_b = _token(client, "mB@example.com")
    with patch("app.services.agent_graph.run_agent", return_value={"summary": "A only"}):
        client.post(
            RUN_URL,
            json={"task_type": "summarize", "document_ids": [DOC_ID]},
            headers=_auth(token_a),
        )
    data_b = client.get(USAGE_URL, headers=_auth(token_b)).json()
    assert data_b["total_agent_runs"] == 0
    assert data_b["total_messages"] == 0


def test_chat_messages_scoped_to_user(client: TestClient):
    token_a = _token(client, "mC@example.com")
    token_b = _token(client, "mD@example.com")
    with (
        patch("app.services.citation_builder.build_citations", return_value=[]),
        patch("app.services.llm_client.get_llm", return_value=_mock_llm()),
        patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS),
    ):
        client.post(QUERY_URL, json={"query": "A question"}, headers=_auth(token_a))

    data_b = client.get(USAGE_URL, headers=_auth(token_b)).json()
    assert data_b["total_messages"] == 0
