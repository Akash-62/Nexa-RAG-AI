"""
Block 3 document ingestion tests.
ChromaDB and embeddings are patched so tests run without external services.
"""
import io
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

REGISTER_URL = "/auth/register"
DOCS_URL = "/documents"
UPLOAD_URL = "/documents/upload"

# ─── Helpers ───────────────────────────────────────────────────────────────────

def _token(client: TestClient, email: str = "doc_user@example.com") -> str:
    r = client.post(REGISTER_URL, json={"name": "Doc User", "email": email, "password": "pass1234"})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _txt_file(content: str = "Hello world. This is a test document.") -> tuple:
    return ("test.txt", io.BytesIO(content.encode()), "text/plain")


# ─── Mocks used by all ingestion tests ─────────────────────────────────────────

MOCK_CHUNKS = [
    {"text": "Hello world.", "document_id": "doc-id", "user_id": "u-id",
     "chunk_index": 0, "page_number": 1, "char_count": 12},
]
MOCK_VECTOR_IDS = ["doc-id_0"]


# ─── Upload tests ───────────────────────────────────────────────────────────────

@patch("app.services.ingestion.add_chunks", return_value=MOCK_VECTOR_IDS)
@patch("app.services.ingestion.chunk_pages", return_value=MOCK_CHUNKS)
@patch("app.services.ingestion.extract_text", return_value=[{"page_number": 1, "text": "Hello world."}])
def test_upload_txt_creates_document(mock_extract, mock_chunk, mock_add, client: TestClient):
    token = _token(client, "upload1@example.com")
    r = client.post(UPLOAD_URL, files={"file": _txt_file()}, headers=_auth(token))
    assert r.status_code == 201
    data = r.json()
    assert "document_id" in data
    assert data["filename"] == "test.txt"
    assert data["status"] == "pending"


@patch("app.services.ingestion.add_chunks", return_value=MOCK_VECTOR_IDS)
@patch("app.services.ingestion.chunk_pages", return_value=MOCK_CHUNKS)
@patch("app.services.ingestion.extract_text", return_value=[{"page_number": 1, "text": "Hello world."}])
def test_upload_document_appears_in_list(mock_extract, mock_chunk, mock_add, client: TestClient):
    token = _token(client, "list1@example.com")
    client.post(UPLOAD_URL, files={"file": _txt_file()}, headers=_auth(token))
    r = client.get(DOCS_URL, headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["documents"][0]["filename"] == "test.txt"


def test_upload_unsupported_extension_returns_400(client: TestClient):
    token = _token(client, "badext@example.com")
    r = client.post(
        UPLOAD_URL,
        files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        headers=_auth(token),
    )
    assert r.status_code == 400


def test_upload_empty_file_returns_400(client: TestClient):
    token = _token(client, "empty@example.com")
    r = client.post(
        UPLOAD_URL,
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers=_auth(token),
    )
    assert r.status_code == 400


def test_upload_without_auth_returns_401(client: TestClient):
    r = client.post(UPLOAD_URL, files={"file": _txt_file()})
    assert r.status_code == 401


# ─── List tests ─────────────────────────────────────────────────────────────────

def test_list_documents_empty_for_new_user(client: TestClient):
    token = _token(client, "empty_list@example.com")
    r = client.get(DOCS_URL, headers=_auth(token))
    assert r.status_code == 200
    assert r.json() == {"documents": [], "total": 0}


def test_list_documents_scoped_to_user(client: TestClient):
    """User A cannot see User B's documents."""
    token_a = _token(client, "usera@example.com")
    token_b = _token(client, "userb@example.com")
    with (
        patch("app.services.ingestion.add_chunks", return_value=MOCK_VECTOR_IDS),
        patch("app.services.ingestion.chunk_pages", return_value=MOCK_CHUNKS),
        patch("app.services.ingestion.extract_text", return_value=[{"page_number": 1, "text": "test"}]),
    ):
        client.post(UPLOAD_URL, files={"file": _txt_file("User A content")}, headers=_auth(token_a))

    r = client.get(DOCS_URL, headers=_auth(token_b))
    assert r.json()["total"] == 0


# ─── Delete tests ───────────────────────────────────────────────────────────────

@patch("app.services.vector_store.delete_document_vectors")
@patch("app.services.ingestion.add_chunks", return_value=MOCK_VECTOR_IDS)
@patch("app.services.ingestion.chunk_pages", return_value=MOCK_CHUNKS)
@patch("app.services.ingestion.extract_text", return_value=[{"page_number": 1, "text": "Hello world."}])
def test_delete_document_removes_it(mock_extract, mock_chunk, mock_add, mock_del, client: TestClient):
    token = _token(client, "del1@example.com")
    upload = client.post(UPLOAD_URL, files={"file": _txt_file()}, headers=_auth(token))
    doc_id = upload.json()["document_id"]

    r = client.delete(f"{DOCS_URL}/{doc_id}", headers=_auth(token))
    assert r.status_code == 204

    r = client.get(DOCS_URL, headers=_auth(token))
    assert r.json()["total"] == 0


@patch("app.services.vector_store.delete_document_vectors")
def test_delete_nonexistent_document_returns_404(mock_del, client: TestClient):
    token = _token(client, "del404@example.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.delete(f"{DOCS_URL}/{fake_id}", headers=_auth(token))
    assert r.status_code == 404


# ─── Chunking unit tests (no DB / HTTP needed) ─────────────────────────────────

def test_chunk_pages_produces_chunks():
    from app.services.chunking import chunk_pages
    pages = [{"page_number": 1, "text": "A" * 2500}]
    chunks = chunk_pages(pages, "test-doc-id", "test-user-id")
    assert len(chunks) >= 2  # 2500 chars → at least 2 chunks at default 1000
    assert all(c["document_id"] == "test-doc-id" for c in chunks)
    assert all(c["page_number"] == 1 for c in chunks)
    assert all(c["char_count"] > 0 for c in chunks)


def test_chunk_pages_empty_page_returns_empty():
    from app.services.chunking import chunk_pages
    chunks = chunk_pages([{"page_number": 1, "text": ""}], "doc", "user")
    assert chunks == []


def test_extract_txt_returns_page():
    import tempfile, os
    from app.services.document_loader import extract_text
    content = "This is a test document.\nWith two lines."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        pages = extract_text(tmp_path, "txt")
        assert len(pages) == 1
        assert pages[0]["page_number"] == 1
        assert "test document" in pages[0]["text"]
    finally:
        os.unlink(tmp_path)
