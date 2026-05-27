import { useState, FormEvent } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import { Eye, EyeOff, Zap, AlertCircle, CheckCircle2 } from "lucide-react";
import { login } from "@/services/api";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const location = useLocation();
  const prefill = (location.state as any) ?? {};
  const [email, setEmail] = useState(prefill.email ?? "");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setToken } = useAuth();
  const navigate = useNavigate();

  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!emailValid) {
      setError("Please enter a valid email address (e.g. you@example.com)");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await login(email, password);
      setToken(res.data.access_token);
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7] flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="flex items-center gap-2.5 mb-8">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-md">
          <Zap size={18} className="text-white" />
        </div>
        <span className="text-lg font-bold text-gray-900 tracking-tight">Nexa RAG AI</span>
      </div>

      {/* Card */}
      <div className="w-full max-w-[400px] bg-white rounded-2xl shadow-[0_2px_24px_rgba(0,0,0,0.08)] border border-gray-100 overflow-hidden">
        {/* Top accent */}
        <div className="h-1 w-full bg-gradient-to-r from-brand-500 via-purple-500 to-indigo-500" />

        <div className="px-8 py-8">
          <h1 className="text-2xl font-bold text-gray-900 tracking-tight">Welcome back</h1>
          <p className="text-sm text-gray-400 mt-1 mb-7">Sign in to your Nexa workspace</p>

          {prefill.registered && (
            <div className="flex items-center gap-2 bg-green-50 border border-green-100 rounded-xl px-3.5 py-3 mb-5 text-sm text-green-700">
              <CheckCircle2 size={15} className="shrink-0" />
              Account created! Sign in to continue.
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-100 rounded-xl px-3.5 py-3 mb-5 text-sm text-red-600">
              <AlertCircle size={15} className="shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Email</label>
              <input
                type="text"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className={`w-full border rounded-xl px-4 py-3 text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 transition-all bg-gray-50 hover:bg-white ${
                  email && !emailValid
                    ? "border-red-300 focus:ring-red-200 focus:border-red-400"
                    : "border-gray-200 focus:ring-brand-500/20 focus:border-brand-400"
                }`}
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  className="w-full border border-gray-200 rounded-xl px-4 py-3 pr-11 text-sm text-gray-900 placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-400 transition-all bg-gray-50 hover:bg-white"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-brand-600 to-purple-600 text-white py-3 rounded-xl text-sm font-semibold hover:opacity-90 disabled:opacity-50 transition-all shadow-md hover:shadow-lg active:scale-[0.98] mt-1"
            >
              {loading ? "Signing in…" : "Sign in →"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-400 mt-6">
            No account?{" "}
            <Link to="/register" className="text-brand-600 font-semibold hover:text-brand-700">
              Create one free
            </Link>
          </p>
        </div>
      </div>

      <p className="mt-6 text-xs text-gray-300">Nexa RAG AI · Document Intelligence Platform</p>
    </div>
  );
}
