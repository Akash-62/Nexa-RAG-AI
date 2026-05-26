# Architecture

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                       │
│  Dashboard  │  Chat (RAG Q&A)  │  Agent Workflows  │  Login/Auth  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼─────────────────────────────────────┐
│                     FastAPI Backend                                │
│  /auth  │  /documents  │  /chat  │  /agent  │  /metrics           │
│  JWT middleware · Pydantic validation · CORS                       │
└──────┬───────────────┬──────────────────────────┬──────────────────┘
       │               │                          │
┌──────▼──────┐  ┌─────▼──────┐         ┌────────▼────────────────┐
│ PostgreSQL  │  │  ChromaDB  │         │   LangGraph Agent Graph  │
│  metadata   │  │  vectors   │         │  classify → retrieve →   │
│  (SQLAlch.) │  │ (chromadb) │         │  answer | summarize |    │
└─────────────┘  └─────▲──────┘         │  compare | actions |    │
                        │               │  email | fallback        │
               ┌────────┴────────┐      └─────────────┬───────────┘
               │  RAG Services   │                    │
               │  document_loader│      ┌─────────────▼───────────┐
               │  chunking       │      │    LLM Client (Factory)  │
               │  embeddings     │      │  OpenAI / Anthropic /    │
               │  retrieval      │      │  Gemini via .env switch  │
               │  citation_builder│     └─────────────────────────┘
               │  confidence     │
               └─────────────────┘
```

## Layers

| Layer | Responsibility | Key Files |
|---|---|---|
| Frontend | UI, auth state, API calls | `frontend/src/` |
| Backend API | Routing, auth, validation | `backend/app/api/` |
| Schemas | Request/response types | `backend/app/schemas/` |
| DB | Persistence, migrations | `backend/app/db/` |
| Services | Business logic | `backend/app/services/` |
| Core | Config, security, logging | `backend/app/core/` |

## Data Flow — RAG Q&A

1. User submits query via `POST /chat/query`
2. `retrieval.py` converts query → embedding, searches ChromaDB top-k
3. `confidence.py` scores relevance; if low → fallback response
4. `citation_builder.py` formats chunks → CitationOut objects
5. `llm_client.py` calls LLM with context-only prompt
6. Response + citations + confidence score returned
7. ChatMessage + Citations written to PostgreSQL
8. `metrics.py` logs token usage + estimated cost

## Data Flow — Agent Workflow

1. User calls `POST /agent/run` with task_type + document_ids
2. LangGraph `classify_query` node confirms task type
3. `retrieve_context` fetches relevant chunks
4. Task-specific node (summarize / compare / actions / email) executes
5. `AgentRun` record written to PostgreSQL
6. Structured JSON output returned

## Key Design Decisions

- **Provider-agnostic LLM**: `llm_client.py` is the only file that imports provider SDKs. Switch model by changing `.env` — no code changes.
- **ChromaDB local for MVP**: Zero-cost, runs in Docker. Swap to Pinecone by adding `PINECONE_API_KEY` and updating `vector_store.py`.
- **Citation traceability**: Every answer links to document_id + page_number + chunk_index so claims are verifiable.
- **Confidence threshold**: Responses below 0.35 cosine similarity return "I don't have enough context" instead of hallucinating.
- **SQLAlchemy sync**: Using synchronous SQLAlchemy (not async) for simplicity and Alembic compatibility. Sufficient for current scale.
