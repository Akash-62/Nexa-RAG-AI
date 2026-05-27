import { useState, FormEvent, useEffect } from "react";
import { runAgent, listDocuments } from "@/services/api";
import { Wand2, Loader2, Copy, Check, AlertCircle } from "lucide-react";

const TASKS = [
  { value: "summarize", label: "Summarize", description: "Key points & findings" },
  { value: "compare", label: "Compare", description: "Similarities & differences" },
  { value: "extract_actions", label: "Extract Actions", description: "Tasks & deadlines" },
  { value: "generate_email", label: "Draft Email", description: "Professional email draft" },
] as const;

type TaskType = (typeof TASKS)[number]["value"];

interface Doc {
  id: string;
  filename: string;
  status: string;
}

// ─── Result renderers ──────────────────────────────────────────────────────────

function SummaryResult({ text }: { text: string }) {
  return (
    <div className="bg-white border rounded-xl p-5 text-sm whitespace-pre-wrap leading-relaxed text-gray-800">
      {text || "No summary generated."}
    </div>
  );
}

function CompareResult({ text }: { text: string }) {
  return (
    <div className="bg-white border rounded-xl p-5 text-sm whitespace-pre-wrap leading-relaxed text-gray-800">
      {text || "No comparison generated."}
    </div>
  );
}

const PRIORITY_STYLE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

function ActionsResult({ items }: { items: any[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-400">No action items found in these documents.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-xl border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-4 py-3">Task</th>
            <th className="px-4 py-3">Owner</th>
            <th className="px-4 py-3">Deadline</th>
            <th className="px-4 py-3">Priority</th>
          </tr>
        </thead>
        <tbody className="divide-y bg-white">
          {items.map((item, i) => (
            <tr key={i}>
              <td className="px-4 py-3 font-medium">{item.task}</td>
              <td className="px-4 py-3 text-gray-500">{item.owner ?? "—"}</td>
              <td className="px-4 py-3 text-gray-500">{item.deadline ?? "—"}</td>
              <td className="px-4 py-3">
                {item.priority ? (
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      PRIORITY_STYLE[item.priority] ?? "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {item.priority}
                  </span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmailResult({ email }: { email: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(email).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div>
      <div className="flex justify-end mb-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-brand-600 hover:text-brand-700 font-medium transition-colors"
        >
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? "Copied!" : "Copy email"}
        </button>
      </div>
      <div className="bg-white border rounded-xl p-5 text-sm whitespace-pre-wrap leading-relaxed font-mono text-gray-800">
        {email || "No email generated."}
      </div>
    </div>
  );
}

function AgentResult({ taskType, output }: { taskType: TaskType; output: any }) {
  if (output?.error) {
    return (
      <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-600">
        <AlertCircle size={15} className="shrink-0 mt-0.5" />
        <span>{output.error}</span>
      </div>
    );
  }

  if (taskType === "summarize")
    return <SummaryResult text={output?.summary ?? ""} />;
  if (taskType === "compare")
    return <CompareResult text={output?.comparison ?? ""} />;
  if (taskType === "extract_actions")
    return <ActionsResult items={output?.action_items ?? []} />;
  if (taskType === "generate_email")
    return <EmailResult email={output?.email ?? ""} />;

  return (
    <pre className="bg-gray-900 text-green-400 text-xs rounded-xl p-4 overflow-x-auto whitespace-pre-wrap">
      {JSON.stringify(output, null, 2)}
    </pre>
  );
}

// ─── Main page ─────────────────────────────────────────────────────────────────

export default function AgentPage() {
  const [task, setTask] = useState<TaskType>("summarize");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [emailContext, setEmailContext] = useState("");
  const [result, setResult] = useState<{ taskType: TaskType; output: any } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then((r) => setDocs(r.data.documents ?? []))
      .catch(() => {});
  }, []);

  function toggleDoc(id: string) {
    setSelectedDocs((s) =>
      s.includes(id) ? s.filter((d) => d !== id) : [...s, id]
    );
  }

  async function handleRun(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const res = await runAgent(
        task,
        selectedDocs,
        query || undefined,
        task === "generate_email" ? emailContext || undefined : undefined
      );
      setResult({ taskType: task, output: res.data.output });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not reach the server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  const readyDocs = docs.filter((d) => d.status === "ready");

  return (
    <div className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-8 max-w-4xl mx-auto w-full">
      <h1 className="text-2xl font-bold mb-1">Agent Workflows</h1>
      <p className="text-sm text-gray-400 mb-6 sm:mb-8">
        Run intelligent document tasks powered by LangGraph
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.4fr] gap-8">
        {/* ── Left: form ── */}
        <form onSubmit={handleRun} className="space-y-6">
          {/* Task type */}
          <div>
            <label className="block text-sm font-medium mb-2">Task</label>
            <div className="grid grid-cols-2 gap-2">
              {TASKS.map(({ value, label, description }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => { setTask(value); setResult(null); }}
                  className={`border rounded-xl px-4 py-3 text-left transition-colors ${
                    task === value
                      ? "border-brand-600 bg-brand-50 text-brand-700"
                      : "hover:border-gray-400 bg-white"
                  }`}
                >
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Documents */}
          <div>
            <label className="block text-sm font-medium mb-2">Documents</label>
            {readyDocs.length === 0 ? (
              <p className="text-sm text-gray-400">
                Upload and process documents from the Dashboard first.
              </p>
            ) : (
              <div className="space-y-1 max-h-44 overflow-y-auto border rounded-xl p-2 bg-white">
                {readyDocs.map((d) => (
                  <label
                    key={d.id}
                    className="flex items-center gap-2 px-2 py-1.5 hover:bg-gray-50 rounded-lg cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedDocs.includes(d.id)}
                      onChange={() => toggleDoc(d.id)}
                      className="accent-brand-600"
                    />
                    <span className="text-sm truncate">{d.filename}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          {/* Optional query */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Focus / question
              <span className="font-normal text-gray-400 ml-1">(optional)</span>
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                task === "compare"
                  ? "e.g. How do the pricing models differ?"
                  : task === "extract_actions"
                  ? "e.g. Focus on actions for the engineering team"
                  : "e.g. Focus on the executive summary"
              }
              rows={2}
              className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
            />
          </div>

          {/* Email context — only for generate_email */}
          {task === "generate_email" && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Email requirements
                <span className="font-normal text-gray-400 ml-1">(optional)</span>
              </label>
              <textarea
                value={emailContext}
                onChange={(e) => setEmailContext(e.target.value)}
                placeholder="e.g. Write a status update email to stakeholders highlighting key risks"
                rows={3}
                className="w-full border rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading || selectedDocs.length === 0}
            className="inline-flex items-center gap-2 bg-brand-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium hover:bg-brand-700 disabled:opacity-50 transition-colors"
          >
            {loading ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Wand2 size={14} />
            )}
            {loading ? "Running agent…" : "Run Agent"}
          </button>
        </form>

        {/* ── Right: result ── */}
        <div className="min-h-[200px]">
          {!result && !error && !loading && (
            <div className="flex items-center justify-center h-full text-gray-300 border-2 border-dashed rounded-2xl">
              <p className="text-sm">Result will appear here</p>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-gray-400">
              <Loader2 size={28} className="animate-spin text-brand-500" />
              <p className="text-sm">Agent is working…</p>
            </div>
          )}

          {error && !loading && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-600">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-medium">
                  {TASKS.find((t) => t.value === result.taskType)?.label} Result
                </h2>
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                  completed
                </span>
              </div>
              <AgentResult taskType={result.taskType} output={result.output} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
