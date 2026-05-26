# API Reference

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

All protected routes require `Authorization: Bearer <token>` header.

---

## Auth

### POST /auth/register
```json
{ "name": "Alice", "email": "alice@example.com", "password": "secret123" }
```
Returns: `{ "access_token": "...", "token_type": "bearer" }`

### POST /auth/login
```json
{ "email": "alice@example.com", "password": "secret123" }
```
Returns: `{ "access_token": "...", "token_type": "bearer" }`

### GET /auth/me
Returns current user info.

---

## Documents

### POST /documents/upload
Multipart form: `file` field.  
Returns: `{ "document_id", "filename", "status", "message" }`

### GET /documents
Returns: `{ "documents": [...], "total": N }`

### DELETE /documents/{id}
Deletes document + removes vectors from ChromaDB.

---

## Chat

### POST /chat/query
```json
{
  "query": "What are the payment terms?",
  "session_id": null,
  "document_ids": ["uuid1", "uuid2"]
}
```
Returns:
```json
{
  "answer": "Payment is due within 30 days...",
  "citations": [
    { "document_id": "...", "filename": "contract.pdf", "page_number": 3,
      "chunk_index": 7, "text_excerpt": "...", "relevance_score": 0.92 }
  ],
  "confidence_score": 0.87,
  "latency_ms": 1240,
  "session_id": "..."
}
```

### GET /chat/sessions
Returns list of chat sessions for current user.

---

## Agent

### POST /agent/run
```json
{
  "task_type": "summarize",
  "document_ids": ["uuid1"],
  "query": "Focus on risks"
}
```
`task_type` options: `summarize` | `compare` | `extract_actions` | `generate_email`

Returns:
```json
{
  "run_id": "...",
  "task_type": "summarize",
  "status": "completed",
  "output": { ... },
  "latency_ms": 3200
}
```

---

## Metrics

### GET /metrics/usage
Returns: `{ "total_tokens_in", "total_tokens_out", "estimated_cost_usd", "total_agent_runs", "total_messages" }`
