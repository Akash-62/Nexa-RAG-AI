"""
LangGraph agent: routes document tasks to four specialized nodes.
All langgraph/langchain imports are lazy so the module loads without them installed.
"""
import json
import logging
import re
from typing import TypedDict

logger = logging.getLogger(__name__)


# ─── Shared state schema ───────────────────────────────────────────────────────

class AgentState(TypedDict):
    task_type: str
    document_ids: list
    query: str | None
    email_context: str | None
    chunks: list
    output: dict
    error: str | None


# ─── Prompts ───────────────────────────────────────────────────────────────────

_SUMMARIZE_PROMPT = """\
You are a document analyst. Summarize the following content concisely, \
highlighting key points, decisions, and findings.

CONTENT:
{context}

Provide a well-structured summary in 3-5 paragraphs.

SUMMARY:"""

_COMPARE_PROMPT = """\
You are a document analyst. Compare and contrast the provided documents, \
highlighting similarities, differences, and key insights.

FOCUS: {query}

DOCUMENTS:
{context}

Provide a structured comparison that covers key themes, agreements, and differences.

COMPARISON:"""

_EXTRACT_ACTIONS_PROMPT = """\
You are a project-management assistant. Extract every action item, task, \
and commitment mentioned in the content below.

CONTENT:
{context}

Return ONLY a valid JSON array. Each element must have exactly these fields:
  task     - string (what must be done)
  owner    - string or null (who is responsible)
  deadline - string or null (due date if mentioned)
  priority - "high" | "medium" | "low" or null
  status   - always "pending"

Example:
[{{"task": "Review proposal", "owner": "Alice", "deadline": "2024-01-15", \
"priority": "high", "status": "pending"}}]

JSON:"""

_GENERATE_EMAIL_PROMPT = """\
You are a professional business writer. Draft a sharp, focused email based \
solely on the document content below.

DOCUMENT CONTENT:
{context}

EMAIL REQUIREMENTS:
{email_context}

ADDITIONAL FOCUS: {query}

Output ONLY the email — no preamble, no "Here is the email:" commentary.
Format rules:
  Line 1:  Subject: <concise subject>
  Line 2:  (blank)
  Line 3+: Salutation, then 2-4 tight paragraphs, then:
           Best regards,
           [Your Name]
           [Your Title]
           [Your Email]
           [Your Phone]
IMPORTANT: Never use any real name, email address, phone number, or personal \
detail found in the document. Always substitute every such field with the \
placeholder shown above (e.g. [Your Name], [Your Email]).
Keep it under 250 words. Use only facts from the document.

EMAIL:"""


# ─── Node helpers ──────────────────────────────────────────────────────────────

def _llm_text(prompt: str, temperature: float = 0.2) -> str:
    from app.services.llm_client import get_llm
    llm = get_llm(temperature=temperature)
    response = llm.invoke(prompt)
    return response.content if hasattr(response, "content") else str(response)


def _context(chunks: list) -> str:
    from app.services.citation_builder import format_context_block
    return format_context_block(chunks)


# ─── Graph nodes ───────────────────────────────────────────────────────────────

def _retrieve(state: AgentState) -> AgentState:
    from app.services.retrieval import retrieve_chunks
    query = state.get("query") or "key information and main points"
    chunks = retrieve_chunks(
        query=query,
        document_ids=state["document_ids"],
        top_k=10,
    )
    return {**state, "chunks": chunks}


def _summarize(state: AgentState) -> AgentState:
    context = _context(state["chunks"])
    if not context:
        return {**state, "output": {"summary": "No content found in the specified documents."}}
    text = _llm_text(_SUMMARIZE_PROMPT.format(context=context), temperature=0.2)
    return {**state, "output": {"summary": text}}


def _compare(state: AgentState) -> AgentState:
    context = _context(state["chunks"])
    if not context:
        return {**state, "output": {"comparison": "No content found in the specified documents."}}
    query = state.get("query") or "Compare these documents"
    text = _llm_text(_COMPARE_PROMPT.format(context=context, query=query), temperature=0.2)
    return {**state, "output": {"comparison": text}}


def _extract_actions(state: AgentState) -> AgentState:
    context = _context(state["chunks"])
    if not context:
        return {**state, "output": {"action_items": []}}
    raw = _llm_text(_EXTRACT_ACTIONS_PROMPT.format(context=context), temperature=0.0)
    try:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        items = json.loads(match.group() if match else raw)
        if not isinstance(items, list):
            items = []
    except (json.JSONDecodeError, AttributeError):
        logger.warning("Could not parse action items JSON; returning empty list")
        items = []
    return {**state, "output": {"action_items": items}}


def _generate_email(state: AgentState) -> AgentState:
    context = _context(state["chunks"])
    email_context = state.get("email_context") or "Write a professional summary email."
    query = state.get("query") or ""
    text = _llm_text(
        _GENERATE_EMAIL_PROMPT.format(
            context=context, email_context=email_context, query=query
        ),
        temperature=0.2,
    )
    return {**state, "output": {"email": text}}


def _route(state: AgentState) -> str:
    return state["task_type"]


# ─── Graph factory ─────────────────────────────────────────────────────────────

def _build_graph():
    from langgraph.graph import StateGraph, END  # lazy — not installed in test venv

    g = StateGraph(AgentState)
    g.add_node("retrieve", _retrieve)
    g.add_node("summarize", _summarize)
    g.add_node("compare", _compare)
    g.add_node("extract_actions", _extract_actions)
    g.add_node("generate_email", _generate_email)

    g.set_entry_point("retrieve")
    g.add_conditional_edges(
        "retrieve",
        _route,
        {
            "summarize": "summarize",
            "compare": "compare",
            "extract_actions": "extract_actions",
            "generate_email": "generate_email",
        },
    )
    for node in ("summarize", "compare", "extract_actions", "generate_email"):
        g.add_edge(node, END)

    return g.compile()


# ─── Public API ────────────────────────────────────────────────────────────────

def run_agent(
    task_type: str,
    document_ids: list[str],
    query: str | None = None,
    email_context: str | None = None,
) -> dict:
    """
    Runs the LangGraph agent for the given task and returns the output dict.
    Output shape depends on task_type:
      summarize       → {"summary": str}
      compare         → {"comparison": str}
      extract_actions → {"action_items": list[dict]}
      generate_email  → {"email": str}
    """
    graph = _build_graph()
    initial: AgentState = {
        "task_type": task_type,
        "document_ids": document_ids,
        "query": query,
        "email_context": email_context,
        "chunks": [],
        "output": {},
        "error": None,
    }
    final = graph.invoke(initial)
    return final["output"]
