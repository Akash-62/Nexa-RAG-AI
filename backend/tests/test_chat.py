"""
Block 4 chat / RAG pipeline tests.
External services (retrieval, LLM) are mocked; the DB is the SQLite test DB.
"""
import uuid
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

REGISTER_URL = "/auth/register"
QUERY_URL = "/chat/query"
SESSIONS_URL = "/chat/sessions"

FAKE_DOC_ID = str(uuid.uuid4())

MOCK_CHUNKS = [
    {
        "text": "The capital of France is Paris.",
        "score": 0.85,
        "metadata": {
            "document_id": FAKE_DOC_ID,
            "chunk_index": 0,
            "page_number": 1,
            "filename": "geography.pdf",
        },
    },
    {
        "text": "Paris has a population of over 2 million.",
        "score": 0.78,
        "metadata": {
            "document_id": FAKE_DOC_ID,
            "chunk_index": 1,
            "page_number": 2,
            "filename": "geography.pdf",
        },
    },
]

LOW_SCORE_CHUNKS = [
    {
        "text": "Unrelated content about something else entirely.",
        "score": 0.15,
        "metadata": {
            "document_id": FAKE_DOC_ID,
            "chunk_index": 0,
            "page_number": 1,
            "filename": "other.pdf",
        },
    },
]

LLM_ANSWER = "Paris is the capital of France."


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _token(client: TestClient, email: str = "chat_user@example.com") -> str:
    r = client.post(REGISTER_URL, json={"name": "Chat User", "email": email, "password": "pass1234"})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _mock_llm(answer: str = LLM_ANSWER) -> MagicMock:
    llm = MagicMock()
    response = MagicMock()
    response.content = answer
    llm.invoke.return_value = response
    return llm


# ─── Happy-path query ───────────────────────────────────────────────────────────

@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_query_returns_answer(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    mock_get_llm.return_value = _mock_llm()
    token = _token(client, "q1@example.com")
    r = client.post(QUERY_URL, json={"query": "What is the capital of France?"}, headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == LLM_ANSWER
    assert "session_id" in data
    assert data["confidence_score"] >= 0.35
    assert data["latency_ms"] >= 0
    assert isinstance(data["citations"], list)


@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_query_creates_new_session(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    mock_get_llm.return_value = _mock_llm()
    token = _token(client, "q2@example.com")
    r = client.post(QUERY_URL, json={"query": "capital?"}, headers=_auth(token))
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    assert session_id  # non-empty UUID string


@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_query_reuses_existing_session(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    mock_get_llm.return_value = _mock_llm()
    token = _token(client, "q3@example.com")

    r1 = client.post(QUERY_URL, json={"query": "First question"}, headers=_auth(token))
    session_id = r1.json()["session_id"]

    r2 = client.post(
        QUERY_URL,
        json={"query": "Follow-up question", "session_id": session_id},
        headers=_auth(token),
    )
    assert r2.json()["session_id"] == session_id


@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_query_llm_is_called_once(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    llm_instance = _mock_llm()
    mock_get_llm.return_value = llm_instance
    token = _token(client, "q9@example.com")
    client.post(QUERY_URL, json={"query": "test"}, headers=_auth(token))
    llm_instance.invoke.assert_called_once()


# ─── Low-confidence / no-chunks fallback ───────────────────────────────────────

@patch("app.services.retrieval.retrieve_chunks", return_value=LOW_SCORE_CHUNKS)
def test_query_low_confidence_returns_fallback(mock_retrieve, client: TestClient):
    from app.api.routes_chat import FALLBACK_ANSWER
    token = _token(client, "q4@example.com")
    r = client.post(QUERY_URL, json={"query": "What is the meaning of life?"}, headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == FALLBACK_ANSWER
    assert data["citations"] == []
    assert data["confidence_score"] < 0.35


@patch("app.services.retrieval.retrieve_chunks", return_value=[])
def test_query_no_chunks_returns_fallback(mock_retrieve, client: TestClient):
    from app.api.routes_chat import FALLBACK_ANSWER
    token = _token(client, "q5@example.com")
    r = client.post(QUERY_URL, json={"query": "Unknown topic"}, headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == FALLBACK_ANSWER
    assert data["confidence_score"] == 0.0


# ─── Auth guard ─────────────────────────────────────────────────────────────────

def test_query_without_auth_returns_401(client: TestClient):
    r = client.post(QUERY_URL, json={"query": "test"})
    assert r.status_code == 401


# ─── Sessions list ───────────────────────────────────────────────────────────────

@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_list_sessions_after_query(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    mock_get_llm.return_value = _mock_llm()
    token = _token(client, "q6@example.com")
    client.post(QUERY_URL, json={"query": "Hello there"}, headers=_auth(token))

    r = client.get(SESSIONS_URL, headers=_auth(token))
    assert r.status_code == 200
    sessions = r.json()
    assert len(sessions) >= 1
    assert "id" in sessions[0]
    assert "title" in sessions[0]
    assert "created_at" in sessions[0]


def test_list_sessions_empty_for_new_user(client: TestClient):
    token = _token(client, "q7@example.com")
    r = client.get(SESSIONS_URL, headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_without_auth_returns_401(client: TestClient):
    r = client.get(SESSIONS_URL)
    assert r.status_code == 401


def test_sessions_scoped_to_user(client: TestClient):
    """User B cannot see User A's sessions."""
    token_a = _token(client, "sessA@example.com")
    token_b = _token(client, "sessB@example.com")
    with (
        patch("app.services.citation_builder.build_citations", return_value=[]),
        patch("app.services.llm_client.get_llm", return_value=_mock_llm()),
        patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS),
    ):
        client.post(QUERY_URL, json={"query": "A's question"}, headers=_auth(token_a))

    r = client.get(SESSIONS_URL, headers=_auth(token_b))
    assert r.json() == []


# ─── Session messages ────────────────────────────────────────────────────────────

@patch("app.services.citation_builder.build_citations", return_value=[])
@patch("app.services.llm_client.get_llm")
@patch("app.services.retrieval.retrieve_chunks", return_value=MOCK_CHUNKS)
def test_get_session_messages_returns_user_and_assistant(mock_retrieve, mock_get_llm, mock_cit, client: TestClient):
    mock_get_llm.return_value = _mock_llm()
    token = _token(client, "q8@example.com")
    q_resp = client.post(QUERY_URL, json={"query": "What is the capital?"}, headers=_auth(token))
    session_id = q_resp.json()["session_id"]

    r = client.get(f"{SESSIONS_URL}/{session_id}/messages", headers=_auth(token))
    assert r.status_code == 200
    messages = r.json()
    assert len(messages) == 2
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles


def test_get_session_messages_wrong_session_returns_404(client: TestClient):
    token = _token(client, "q10@example.com")
    fake_session_id = str(uuid.uuid4())
    r = client.get(f"{SESSIONS_URL}/{fake_session_id}/messages", headers=_auth(token))
    assert r.status_code == 404


def test_get_session_messages_without_auth_returns_401(client: TestClient):
    fake_session_id = str(uuid.uuid4())
    r = client.get(f"{SESSIONS_URL}/{fake_session_id}/messages")
    assert r.status_code == 401


# ─── Confidence unit tests ───────────────────────────────────────────────────────

def test_compute_confidence_empty_returns_zero():
    from app.services.confidence import compute_confidence
    assert compute_confidence([]) == 0.0


def test_compute_confidence_single_chunk():
    from app.services.confidence import compute_confidence
    assert compute_confidence([{"score": 0.75}]) == 0.75


def test_compute_confidence_uses_top3_mean():
    from app.services.confidence import compute_confidence
    chunks = [
        {"score": 0.9},
        {"score": 0.8},
        {"score": 0.7},
        {"score": 0.1},  # not in top-3, should not affect result
    ]
    result = compute_confidence(chunks)
    assert result == round((0.9 + 0.8 + 0.7) / 3, 4)


def test_is_low_confidence_below_threshold():
    from app.services.confidence import is_low_confidence
    assert is_low_confidence(0.34) is True


def test_is_low_confidence_at_threshold():
    from app.services.confidence import is_low_confidence
    assert is_low_confidence(0.35) is False


def test_is_low_confidence_above_threshold():
    from app.services.confidence import is_low_confidence
    assert is_low_confidence(0.90) is False
