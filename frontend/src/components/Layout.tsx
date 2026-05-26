import { useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, MessageSquare, Wand2, LogOut, Menu, X } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import clsx from "clsx";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/chat", label: "Chat", icon: MessageSquare, end: false },
  { to: "/agent", label: "Agent", icon: Wand2, end: false },
];

export default function Layout() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex h-screen">
      {/* ── Desktop sidebar ── */}
      <aside className="hidden md:flex w-56 flex-col bg-gray-900 text-white shrink-0">
        <div className="px-5 py-5 border-b border-gray-700">
          <span className="font-bold text-lg tracking-tight">Nexa RAG</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  isActive ? "bg-brand-600 text-white" : "text-gray-300 hover:bg-gray-700"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-5 py-4 text-sm text-gray-400 hover:text-white border-t border-gray-700 transition-colors"
        >
          <LogOut size={16} /> Logout
        </button>
      </aside>

      {/* ── Mobile drawer overlay ── */}
      {drawerOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="w-64 bg-gray-900 text-white flex flex-col">
            <div className="px-5 py-4 border-b border-gray-700 flex items-center justify-between">
              <span className="font-bold text-lg tracking-tight">Nexa RAG</span>
              <button onClick={() => setDrawerOpen(false)}>
                <X size={18} className="text-gray-400 hover:text-white" />
              </button>
            </div>
            <nav className="flex-1 py-4 space-y-1 px-2">
              {navItems.map(({ to, label, icon: Icon, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setDrawerOpen(false)}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                      isActive ? "bg-brand-600 text-white" : "text-gray-300 hover:bg-gray-700"
                    )
                  }
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              ))}
            </nav>
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-5 py-4 text-sm text-gray-400 hover:text-white border-t border-gray-700 transition-colors"
            >
              <LogOut size={16} /> Logout
            </button>
          </div>
          {/* Backdrop */}
          <div className="flex-1 bg-black/50" onClick={() => setDrawerOpen(false)} />
        </div>
      )}

      {/* ── Right panel (top bar + content) ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="md:hidden flex items-center justify-between px-4 py-3 bg-gray-900 text-white shrink-0">
          <span className="font-bold text-base tracking-tight">Nexa RAG</span>
          <button onClick={() => setDrawerOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
        </header>

        <main className="flex-1 overflow-auto bg-gray-50">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
