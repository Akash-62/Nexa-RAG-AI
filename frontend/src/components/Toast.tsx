import { useEffect, useState } from "react";
import { CheckCircle2, X, Coffee, FileText } from "lucide-react";

export type ToastType = "processing" | "success";

export interface ToastData {
  type: ToastType;
  filename: string;
}

interface Props {
  toast: ToastData | null;
  onClose: () => void;
}

export default function Toast({ toast, onClose }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (toast) {
      setVisible(true);
    } else {
      setVisible(false);
    }
  }, [toast]);

  useEffect(() => {
    if (toast?.type === "success") {
      const t = setTimeout(() => onClose(), 5000);
      return () => clearTimeout(t);
    }
  }, [toast, onClose]);

  if (!toast) return null;

  const isSuccess = toast.type === "success";

  return (
    <div
      className={`fixed bottom-24 md:bottom-6 right-4 md:right-6 z-[200] max-w-sm w-[calc(100vw-2rem)] transition-all duration-500 ${
        visible ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"
      }`}
    >
      <div className={`rounded-2xl shadow-2xl overflow-hidden border ${
        isSuccess ? "bg-white border-green-100" : "bg-white border-gray-100"
      }`}>
        {/* Top gradient bar */}
        <div className={`h-1 w-full ${
          isSuccess
            ? "bg-gradient-to-r from-green-400 to-emerald-500"
            : "bg-gradient-to-r from-brand-500 via-purple-500 to-indigo-500 animate-pulse"
        }`} />

        <div className="p-4 flex items-start gap-3.5">
          {/* Icon */}
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
            isSuccess
              ? "bg-gradient-to-br from-green-400 to-emerald-500"
              : "bg-gradient-to-br from-brand-500 to-purple-600"
          }`}>
            {isSuccess
              ? <CheckCircle2 size={20} className="text-white" />
              : <Coffee size={20} className="text-white" />
            }
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900">
              {isSuccess ? "Document ready!" : "Processing your document…"}
            </p>
            <p className="text-xs text-gray-500 mt-0.5 truncate">{toast.filename}</p>
            <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
              {isSuccess
                ? "Your document is ready. Start asking questions in Chat!"
                : "Grab a coffee ☕ or chat with Nexa while we process. We'll notify you when done."}
            </p>

            {!isSuccess && (
              <div className="mt-2.5 flex items-center gap-2">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <div
                      key={i}
                      className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-bounce"
                      style={{ animationDelay: `${i * 150}ms`, animationDuration: "1s" }}
                    />
                  ))}
                </div>
                <span className="text-[11px] text-gray-400">Chunking & embedding…</span>
              </div>
            )}

            {isSuccess && (
              <div className="mt-2">
                <div className="flex items-center gap-1.5 text-[11px] text-emerald-600 font-medium">
                  <FileText size={11} />
                  Ready to query
                </div>
              </div>
            )}
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            className="text-gray-300 hover:text-gray-500 transition-colors shrink-0 mt-0.5"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
