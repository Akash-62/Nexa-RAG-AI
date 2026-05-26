import { createContext, useContext, useState, useCallback } from "react";

interface AuthCtx {
  token: string | null;
  setToken: (t: string | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  token: null,
  setToken: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(
    () => localStorage.getItem("token")
  );

  const setToken = useCallback((t: string | null) => {
    if (t) localStorage.setItem("token", t);
    else localStorage.removeItem("token");
    setTokenState(t);
  }, []);

  const logout = useCallback(() => setToken(null), [setToken]);

  return (
    <AuthContext.Provider value={{ token, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
