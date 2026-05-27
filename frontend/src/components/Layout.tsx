import { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, MessageSquare, Wand2, LogOut, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import clsx from "clsx";
import ConfirmModal from "@/components/ConfirmModal";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/chat", label: "Chat", icon: MessageSquare, end: false },
  { to: "/agent", label: "Agent", icon: Wand2, end: false },
];

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden">

      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-56 flex-col bg-white border-r border-gray-100 shrink-0">
        <div className="px-5 py-5 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-500 to-purple-600 flex items-center justify-center shadow-sm">
              <Zap size={15} className="text-white" />
            </div>
            <span className="font-bold text-base tracking-tight text-gray-900">Nexa RAG</span>
          </div>
        </div>
        <nav className="flex-1 py-4 space-y-0.5 px-3">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                  isActive ? "bg-brand-50 text-brand-700" : "text-gray-500 hover:bg-gray-50 hover:text-gray-800"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={16} strokeWidth={isActive ? 2.5 : 1.8} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => setShowLogoutModal(true)}
          className="flex items-center gap-3 mx-3 mb-4 px-3 py-2.5 text-sm font-medium text-gray-400 hover:text-gray-700 hover:bg-gray-50 rounded-xl transition-all"
        >
          <LogOut size={16} strokeWidth={1.8} />
          Logout
        </button>
      </aside>

      {/* ── Right panel ── */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">

        {/* Page content */}
        <main className="flex-1 overflow-hidden flex flex-col min-h-0">
          <Outlet />
        </main>

        {/* ── Mobile bottom nav (in flex flow, not fixed) ── */}
        <nav
          className="md:hidden shrink-0 bg-white border-t border-gray-100 flex items-stretch"
          style={{ paddingBottom: "env(safe-area-inset-bottom)", height: "calc(56px + env(safe-area-inset-bottom))" }}
        >
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-semibold tracking-wide transition-colors",
                  isActive ? "text-brand-600" : "text-gray-400"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={20} strokeWidth={isActive ? 2.5 : 1.8} />
                  <span>{label}</span>
                </>
              )}
            </NavLink>
          ))}
          <button
            onClick={() => setShowLogoutModal(true)}
            className="flex-1 flex flex-col items-center justify-center gap-0.5 text-[10px] font-semibold tracking-wide text-gray-400"
          >
            <LogOut size={20} strokeWidth={1.8} />
            <span>Logout</span>
          </button>
        </nav>
      </div>

      <ConfirmModal
        open={showLogoutModal}
        variant="logout"
        title="Logout"
        message="You'll need to sign in again to access your documents and chat history."
        confirmLabel="Yes, logout"
        onConfirm={handleLogout}
        onCancel={() => setShowLogoutModal(false)}
      />
    </div>
  );
}
