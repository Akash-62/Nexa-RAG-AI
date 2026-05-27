import { Trash2, LogOut, X } from "lucide-react";

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: "danger" | "logout";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmModal({
  open, title, message, confirmLabel = "Confirm",
  variant = "danger", onConfirm, onCancel,
}: Props) {
  if (!open) return null;

  const isLogout = variant === "logout";

  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={onCancel} />

      {/* Modal — bottom sheet on mobile, centered on desktop */}
      <div className="relative bg-white w-full sm:max-w-sm sm:rounded-2xl rounded-t-2xl shadow-2xl overflow-hidden">
        <button
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-300 hover:text-gray-500 transition-colors"
        >
          <X size={18} />
        </button>

        <div className="px-6 pt-7 pb-2">
          {isLogout ? (
            <>
              {/* Gradient icon for logout */}
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center mb-5 shadow-md">
                <LogOut size={24} className="text-white" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">See you soon!</h2>
              <p className="text-sm text-gray-500 mt-2 leading-relaxed mb-1">{message}</p>
            </>
          ) : (
            <>
              <div className="w-12 h-12 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
                <Trash2 size={22} className="text-red-500" />
              </div>
              <h2 className="text-lg font-bold text-gray-900 leading-tight">{title}</h2>
              <p className="text-sm text-gray-500 mt-2 leading-relaxed">{message}</p>
            </>
          )}
        </div>

        <div className="flex flex-col gap-2 px-6 py-5">
          <button
            onClick={onConfirm}
            className={`w-full py-3 rounded-xl text-white text-sm font-semibold active:scale-[0.98] transition-all shadow-sm ${
              isLogout
                ? "bg-gradient-to-r from-brand-600 to-purple-600 hover:opacity-90"
                : "bg-red-500 hover:bg-red-600"
            }`}
          >
            {confirmLabel}
          </button>
          <button
            onClick={onCancel}
            className="w-full py-3 rounded-xl bg-gray-100 text-gray-700 text-sm font-medium hover:bg-gray-200 active:scale-[0.98] transition-all"
          >
            {isLogout ? "Stay logged in" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
