import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}` : "/api",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ─── Auth ───────────────────────────────────────────────────────────────────

export const register = (name: string, email: string, password: string) =>
  api.post<{ access_token: string }>("/auth/register", { name, email, password });

export const login = (email: string, password: string) =>
  api.post<{ access_token: string }>("/auth/login", { email, password });

export const getMe = () => api.get("/auth/me");

// ─── Documents ──────────────────────────────────────────────────────────────

export const uploadDocument = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("/documents/upload", fd);
};

export const listDocuments = () => api.get("/documents");

export const deleteDocument = (id: string) => api.delete(`/documents/${id}`);

// ─── Chat ───────────────────────────────────────────────────────────────────

export const queryRAG = (
  query: string,
  sessionId?: string,
  documentIds?: string[],
) =>
  api.post("/chat/query", {
    query,
    session_id: sessionId,
    document_ids: documentIds,
  });

export const listSessions = () => api.get("/chat/sessions");

export const getSessionMessages = (sessionId: string) =>
  api.get(`/chat/sessions/${sessionId}/messages`);

// ─── Agent ──────────────────────────────────────────────────────────────────

export const runAgent = (
  taskType: string,
  documentIds: string[],
  query?: string,
  emailContext?: string,
) =>
  api.post("/agent/run", {
    task_type: taskType,
    document_ids: documentIds,
    query,
    email_context: emailContext,
  });

export const listRuns = () => api.get("/agent/runs");

// ─── Metrics ────────────────────────────────────────────────────────────────

export const getUsage = () => api.get("/metrics/usage");

export default api;
