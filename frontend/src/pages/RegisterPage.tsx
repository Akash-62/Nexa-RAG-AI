import { useState, FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, Zap, AlertCircle, CheckCircle2 } from "lucide-react";
import { register } from "@/services/api";
import { useAuth } from "@/context/AuthContext";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { setToken } = useAuth();
  const navigate = useNavigate();

  const strength = password.length === 0 ? 0 : password.length < 6 ? 1 : password.length < 10 ? 2 : 3;
  const strengthLabel = ["", "Weak", "Fair", "Strong"];
  const strengthColor = ["", "bg-red-400", "bg-yellow-400", "bg-green-500"];

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await register(name, email, password);
      setToken(res.data.access_token);
      navigate("/");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-brand-600 to-brand-800 flex-col items-center justify-center p-12 text-white">
        <div className="w-16 h-16 bg-white/20 backdrop-blur rounded-2xl flex items-center justify-center mb-6">
          <Zap size={32} className="text-white" />
        </div>
        <h1 className="text-4xl font-bold mb-3">Nexa RAG AI</h1>
        <p className="text-brand-100 text-center text-lg max-w-sm leading-relaxed">
          Document intelligence powered by RAG. Upload files, ask anything, get cited answers.
        </p>
        <div className="mt-12 space-y-4 w-full max-w-sm">
          {["Free to get started — no credit card", "Upload PDF, DOCX, or TXT files", "Powered by Groq · OpenAI · Anthropic"].map((f) => (
            <div key={f} className="flex items-center gap-3 bg-white/10 rounded-xl px-4 py-3 text-sm">
              <CheckCircle2 size={15} className="text-brand-300 shrink-0" />
              {f}
            </div>
          ))}
        </div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-6 bg-gray-50">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-9 h-9 bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl flex items-center justify-center">
              <Zap size={18} className="text-white" />
            </div>
            <span className="font-bold text-lg">Nexa RAG AI</span>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-1">Create your account</h2>
            <p className="text-sm text-gray-500 mb-7">Start using Nexa RAG AI for free</p>

            {error && (
              <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 rounded-xl px-4 py-3 mb-5 text-sm text-red-700">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Full name</label>
                <input
                  type="text"
                  placeholder="John Doe"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50 focus:bg-white transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Email address</label>
                <input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full border rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50 focus:bg-white transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="Min. 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={8}
                    required
                    className="w-full border rounded-xl px-4 py-2.5 pr-11 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-gray-50 focus:bg-white transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {password.length > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex gap-1 flex-1">
                      {[1, 2, 3].map((s) => (
                        <div
                          key={s}
                          className={`h-1 flex-1 rounded-full transition-all ${strength >= s ? strengthColor[strength] : "bg-gray-200"}`}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-gray-400">{strengthLabel[strength]}</span>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-brand-700 disabled:opacity-60 transition-all shadow-sm hover:shadow-md active:scale-[0.99] mt-2"
              >
                {loading ? "Creating account…" : "Create account"}
              </button>
            </form>

            <p className="text-center text-sm text-gray-500 mt-6">
              Already have an account?{" "}
              <Link to="/login" className="text-brand-600 font-semibold hover:underline">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
