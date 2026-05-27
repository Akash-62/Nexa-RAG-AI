import { useState, FormEvent, useRef, useEffect, useCallback } from "react";
import { queryRAG, listDocuments, getSessionMessages } from "@/services/api";
import { Send, FileText, ChevronDown, ChevronUp, Filter, AlertCircle, Sparkles, User, Trash2 } from "lucide-react";

interface Citation {
  filename: string;
  page_number: number | null;
  text_excerpt: string;
  relevance_score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence_score?: number;
}

interface Doc {
  id: string;
  filename: string;
  status: string;
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const style =
    score >= 0.7
      ? "bg-green-100 text-green-700"
      : score >= 0.35
      ? "bg-yellow-100 text-yellow-700"
      : "bg-red-100 text-red-700";
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style}`}>
      {pct}% confidence
    </span>
  );
}

function CitationPanel({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-2 pt-2 border-t border-gray-100">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors"
      >
        <FileText size={11} />
        {citations.length} source{citations.length !== 1 ? "s" : ""}
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {citations.map((c, i) => (
            <div key={i} className="text-xs bg-gray-50 rounded-lg p-2.5">
              <p className="font-medium text-gray-600">
                {c.filename}
                {c.page_number != null && ` · p.${c.page_number}`}
                <span className="font-normal text-gray-400 ml-2">
                  {Math.round(c.relevance_score * 100)}% match
                </span>
              </p>
              <p className="text-gray-500 mt-1 italic leading-relaxed">
                "{c.text_excerpt.slice(0, 140)}{c.text_excerpt.length > 140 ? "…" : ""}"
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

function loadCachedMessages(): Message[] {
  try {
    const raw = localStorage.getItem("chat_messages");
    if (!raw) return [];
    return JSON.parse(raw) as Message[];
  } catch {
    return [];
  }
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(loadCachedMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(
    localStorage.getItem("chat_session_id") ?? undefined
  );
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [showFilter, setShowFilter] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const readyDocs = docs.filter((d) => d.status === "ready");

  useEffect(() => {
    listDocuments()
      .then((r) => setDocs(r.data.documents ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("chat_session_id");
    if (!saved) return;
    getSessionMessages(saved)
      .then((r) => {
        const msgs = r.data as any[];
        if (msgs.length === 0) return;
        const restored = msgs.map((m) => ({
          role: m.role as "user" | "assistant",
          content: m.content,
          confidence_score: m.confidence_score,
        }));
        setMessages(restored);
        localStorage.setItem("chat_messages", JSON.stringify(restored));
      })
      .catch((err: any) => {
        if (err?.response?.status === 404) {
          localStorage.removeItem("chat_session_id");
          localStorage.removeItem("chat_messages");
          setMessages([]);
        }
      });
  }, []);

  useEffect(() => {
    if (messages.length > 0)
      localStorage.setItem("chat_messages", JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function clearChat() {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
    localStorage.removeItem("chat_session_id");
    localStorage.removeItem("chat_messages");
  }

  const toggleDoc = useCallback((id: string) => {
    setSelectedDocs((s) =>
      s.includes(id) ? s.filter((d) => d !== id) : [...s, id]
    );
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const query = input.trim();
    if (!query) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: query }]);
    setLoading(true);
    try {
      const res = await queryRAG(
        query,
        sessionId,
        selectedDocs.length > 0 ? selectedDocs : undefined
      );
      setSessionId(res.data.session_id);
      localStorage.setItem("chat_session_id", res.data.session_id);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.data.answer,
          citations: res.data.citations,
          confidence_score: res.data.confidence_score,
        },
      ]);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 max-w-3xl w-full mx-auto bg-white">
      {/* Header */}
      <div className="px-4 sm:px-6 py-4 border-b bg-white flex items-center justify-between gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-sm shrink-0">
            <Sparkles size={16} className="text-white" />
          </div>
          <div>
            <h1 className="font-semibold leading-tight">Document Q&amp;A</h1>
            <p className="text-xs text-gray-400 hidden sm:block">Answers grounded in your uploaded documents</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
        {messages.length > 0 && (
          <button
            onClick={clearChat}
            title="Clear chat"
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border text-gray-500 hover:border-red-300 hover:text-red-500 transition-colors shrink-0"
          >
            <Trash2 size={12} />
            <span className="hidden sm:inline">Clear</span>
          </button>
        )}
        {readyDocs.length > 0 && (
          <button
            onClick={() => setShowFilter((f) => !f)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors shrink-0 ${
              showFilter
                ? "bg-brand-50 border-brand-600 text-brand-700"
                : "text-gray-500 hover:border-gray-400"
            }`}
          >
            <Filter size={12} />
            <span className="hidden sm:inline">Filter docs</span>
            <span className="sm:hidden">Filter</span>
            {selectedDocs.length > 0 && (
              <span className="ml-1 bg-brand-600 text-white text-[10px] px-1.5 py-0.5 rounded-full">
                {selectedDocs.length}
              </span>
            )}
          </button>
        )}
        </div>
      </div>

      {/* Document filter panel */}
      {showFilter && readyDocs.length > 0 && (
        <div className="px-4 sm:px-6 py-3 border-b bg-gray-50 shrink-0">
          <p className="text-xs text-gray-500 mb-2">
            Select documents to search (leave all unchecked to search everything):
          </p>
          <div className="flex flex-wrap gap-2">
            {readyDocs.map((d) => (
              <label
                key={d.id}
                className="flex items-center gap-1.5 text-xs cursor-pointer bg-white border rounded-lg px-2.5 py-1.5 hover:border-brand-400 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selectedDocs.includes(d.id)}
                  onChange={() => toggleDoc(d.id)}
                  className="accent-brand-600"
                />
                <span className="truncate max-w-[160px]">{d.filename}</span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-5">
        {messages.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-center py-16">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-md">
              <Sparkles size={26} className="text-white" />
            </div>
            <div>
              <p className="font-semibold text-gray-700">Ask Nexa anything</p>
              <p className="text-sm text-gray-400 mt-1">
                Upload documents on the Dashboard, then ask a question here.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex items-end gap-2.5 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            {/* Assistant avatar */}
            {msg.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0 mb-0.5 shadow-sm">
                <Sparkles size={13} className="text-white" />
              </div>
            )}

            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                msg.role === "user"
                  ? "bg-brand-600 text-white rounded-br-sm"
                  : "bg-white border rounded-bl-sm"
              }`}
            >
              <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

              {msg.role === "assistant" && msg.confidence_score !== undefined && (
                <div className="mt-2">
                  <ConfidenceBadge score={msg.confidence_score} />
                </div>
              )}

              {msg.citations && msg.citations.length > 0 && (
                <CitationPanel citations={msg.citations} />
              )}
            </div>

            {/* User avatar */}
            {msg.role === "user" && (
              <div className="w-7 h-7 rounded-lg bg-brand-700 flex items-center justify-center shrink-0 mb-0.5 shadow-sm">
                <User size={13} className="text-white" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-end gap-2.5 justify-start">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shrink-0 shadow-sm">
              <Sparkles size={13} className="text-white" />
            </div>
            <div className="bg-white border shadow-sm rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2">
              <div className="flex gap-1 items-center">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-2 h-2 bg-brand-500 rounded-full animate-bounce"
                    style={{ animationDelay: `${delay}ms`, animationDuration: "0.9s" }}
                  />
                ))}
              </div>
              <span className="text-xs text-gray-400 ml-1">Thinking…</span>
            </div>
          </div>
        )}

        {error && (
          <div className="flex justify-start">
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-2xl px-4 py-3 text-sm text-red-600 max-w-[80%]">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="px-4 sm:px-6 py-4 border-t bg-white flex gap-2 sm:gap-3 shrink-0"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents…"
          disabled={loading}
          className="flex-1 border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-60 bg-gray-50 focus:bg-white transition-colors"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="w-10 h-10 flex items-center justify-center rounded-xl bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40 transition-all shadow-sm hover:shadow-md active:scale-95 shrink-0"
          aria-label="Send"
        >
          <Send size={17} strokeWidth={2.2} />
        </button>
      </form>
    </div>
  );
}
