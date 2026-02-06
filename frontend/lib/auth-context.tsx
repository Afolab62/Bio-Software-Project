"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  type ReactNode,
} from "react";

interface AuthUser {
  id: string;
  email: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  login: (
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string }>;
  register: (
    email: string,
    password: string,
  ) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const stored = sessionStorage.getItem("de_portal_user");
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        sessionStorage.removeItem("de_portal_user");
      }
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (data.success && data.user) {
        setUser(data.user);
        sessionStorage.setItem("de_portal_user", JSON.stringify(data.user));
        return { success: true };
      }

      return { success: false, error: data.error || "Login failed" };
    } catch (error) {
      console.error("Login error:", error);
      return {
        success: false,
        error: "Network error - unable to connect to server",
      };
    }
  };

  const register = async (email: string, password: string) => {
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (data.success && data.user) {
        setUser(data.user);
        sessionStorage.setItem("de_portal_user", JSON.stringify(data.user));
        return { success: true };
      }

      return { success: false, error: data.error || "Registration failed" };
    } catch (error) {
      console.error("Registration error:", error);
      return {
        success: false,
        error: "Network error - unable to connect to server",
      };
    }
  };

  const logout = () => {
    setUser(null);
    sessionStorage.removeItem("de_portal_user");
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
