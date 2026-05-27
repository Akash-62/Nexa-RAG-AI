import { useEffect, useState, useCallback, useRef, DragEvent } from "react";
import { listDocuments, uploadDocument, deleteDocument, getUsage } from "@/services/api";
import { FileText, Trash2, Loader2, AlertCircle, UploadCloud } from "lucide-react";

interface Doc {
  id: string;
  filename: string;
  file_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

interface RecentOp {
  operation: string;
  model: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  created_at: string;
}

interface Usage {
  total_tokens_in: number;
  total_tokens_out: number;
  total_tokens: number;
  estimated_cost_usd: number;
  total_calls: number;
  total_agent_runs: number;
  total_messages: number;
  avg_latency_ms: number;
  recent_operations: RecentOp[];
}

const STATUS_COLOR: Record<string, string> = {
  ready: "text-green-600",
  failed: "text-red-500",
  pending: "text-yellow-500",
  processing: "text-yellow-500",
};

export default function DashboardPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [d, u] = await Promise.all([listDocuments(), getUsage()]);
      setDocs(d.data.documents ?? []);
      setUsage(u.data);
    } catch {
      // silently ignore — user will see stale data
    }
  }, []);

  // Poll while any document is still processing
  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  useEffect(() => {
    const hasPending = docs.some(
      (d) => d.status === "pending" || d.status === "processing"
    );
    if (hasPending && !pollRef.current) {
      pollRef.current = setInterval(fetchAll, 3000);
    } else if (!hasPending && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [docs, fetchAll]);

  async function handleFile(file: File) {
    setUploadError(null);
    setUploading(true);
    try {
      await uploadDocument(file);
      await fetchAll();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setUploadError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join(", ")
          : "Upload failed. Check file type and size."
      );
    } finally {
      setUploading(false);
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function onDragLeave() {
    setDragging(false);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  async function handleDelete(id: string) {
    try {
      await deleteDocument(id);
      setDocs((d) => d.filter((doc) => doc.id !== id));
    } catch {
      // leave list unchanged; the server will respond next poll
    }
  }

  return (
    <div className="p-4 sm:p-8 max-w-5xl mx-auto overflow-y-auto h-full">
      <h1 className="text-2xl font-bold mb-2">Dashboard</h1>
      <p className="text-sm text-gray-400 mb-6 sm:mb-8">Manage your documents and view usage stats</p>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4 mb-6 sm:mb-8">
        {[
          { label: "Documents", value: docs.length },
          { label: "Messages", value: usage?.total_messages ?? "—" },
          { label: "Agent Runs", value: usage?.total_agent_runs ?? "—" },
          {
            label: "Tokens Used",
            value: usage != null ? (usage.total_tokens).toLocaleString() : "—",
          },
          {
            label: "Avg Latency",
            value: usage != null ? `${usage.avg_latency_ms} ms` : "—",
          },
          {
            label: "Est. Cost",
            value: usage != null ? `$${usage.estimated_cost_usd.toFixed(4)}` : "—",
          },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-xl border p-4 shadow-sm">
            <p className="text-xs text-gray-500 mb-1">{label}</p>
            <p className="text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>

      {/* Upload zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        className={`mb-6 border-2 border-dashed rounded-2xl p-6 transition-colors ${
          dragging
            ? "border-brand-500 bg-brand-50"
            : "border-gray-200 hover:border-gray-300 bg-white"
        }`}
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <UploadCloud
            size={32}
            className={dragging ? "text-brand-500" : "text-gray-300"}
          />
          <div>
            <p className="text-sm text-gray-600">
              Drag & drop a file here, or{" "}
              <label className="text-brand-600 font-medium cursor-pointer hover:underline">
                browse
                <input
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={handleInputChange}
                  disabled={uploading}
                  className="hidden"
                />
              </label>
            </p>
            <p className="text-xs text-gray-400 mt-1">PDF, DOCX, or TXT up to 50 MB</p>
          </div>
          {uploading && (
            <div className="flex items-center gap-2 text-sm text-brand-600">
              <Loader2 size={14} className="animate-spin" />
              Uploading and queuing ingestion…
            </div>
          )}
        </div>
      </div>

      {uploadError && (
        <div className="flex items-start gap-2 mb-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-600">
          <AlertCircle size={15} className="shrink-0 mt-0.5" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Document list */}
      <div className="bg-white rounded-xl border shadow-sm divide-y">
        {docs.length === 0 ? (
          <p className="text-center text-gray-400 py-14 text-sm">
            No documents yet — upload your first file above.
          </p>
        ) : (
          docs.map((doc) => (
            <div key={doc.id} className="flex items-center gap-4 px-5 py-3.5">
              <FileText size={18} className="text-brand-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{doc.filename}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {doc.file_type.toUpperCase()} · {doc.chunk_count} chunk
                  {doc.chunk_count !== 1 ? "s" : ""} ·{" "}
                  <span className={STATUS_COLOR[doc.status] ?? "text-gray-400"}>
                    {doc.status}
                    {(doc.status === "pending" || doc.status === "processing") && (
                      <Loader2 size={10} className="inline ml-1 animate-spin" />
                    )}
                  </span>
                </p>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-gray-300 hover:text-red-500 transition-colors"
                title="Delete document"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))
        )}
      </div>

      {/* Recent LLM activity */}
      {usage && usage.recent_operations.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold mb-3 text-gray-700">Recent LLM Activity</h2>
          <div className="bg-white rounded-xl border shadow-sm divide-y">
            {usage.recent_operations.map((op, i) => (
              <div key={i} className="flex items-center gap-4 px-5 py-3 text-sm">
                <div className="flex-1 min-w-0">
                  <span className="font-medium capitalize">{op.operation.replace("_", " ")}</span>
                  <span className="text-gray-400 text-xs ml-2">{op.model}</span>
                </div>
                <div className="text-xs text-gray-500 text-right shrink-0">
                  <p>{(op.tokens_in + op.tokens_out).toLocaleString()} tokens</p>
                  <p className="text-gray-400">${op.cost_usd.toFixed(5)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
