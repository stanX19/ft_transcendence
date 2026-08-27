import {
  createContext,
  type FormEvent,
  type PropsWithChildren,
  useCallback,
  useContext,
} from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiRequest } from "../../shared/api";
import type { AuthUser } from "../../shared/types";

const AUTH_QUERY_KEY = ["auth", "me"] as const;

interface AuthResponse {
  user?: AuthUser;
  id?: number;
  email?: string;
  display_name?: string;
  bio?: string;
  role?: string;
  is_online?: boolean;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  error: Error | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (
    displayName: string,
    email: string,
    password: string,
  ) => Promise<AuthUser>;
  logout: () => Promise<void>;
  setUser: (user: AuthUser | null) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function unwrapUser(payload: AuthResponse): AuthUser {
  const user = payload.user ?? payload;
  if (
    typeof user.id !== "number" ||
    typeof user.email !== "string" ||
    typeof user.display_name !== "string" ||
    typeof user.role !== "string"
  ) {
    throw new Error("The authentication response was incomplete.");
  }

  return {
    id: user.id,
    email: user.email,
    display_name: user.display_name,
    bio: typeof user.bio === "string" ? user.bio : "",
    role: user.role,
    is_online: user.is_online === true,
  };
}

async function fetchCurrentUser(): Promise<AuthUser | null> {
  try {
    const payload = await apiRequest<AuthResponse>("/api/auth/me");
    return unwrapUser(payload);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient();
  const authQuery = useQuery({
    queryKey: AUTH_QUERY_KEY,
    queryFn: fetchCurrentUser,
    retry: false,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });

  const setUser = useCallback(
    (user: AuthUser | null) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
    },
    [queryClient],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const payload = await apiRequest<AuthResponse>("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
      });
      const user = unwrapUser(payload);
      setUser(user);
      return user;
    },
    [setUser],
  );

  const register = useCallback(
    async (displayName: string, email: string, password: string) => {
      const payload = await apiRequest<AuthResponse>("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          display_name: displayName.trim(),
          email: email.trim().toLowerCase(),
          password,
        }),
      });
      const user = unwrapUser(payload);
      setUser(user);
      return user;
    },
    [setUser],
  );

  const logout = useCallback(async () => {
    await apiRequest("/api/auth/logout", {
      method: "POST",
      credentials: "include",
    });
    setUser(null);
  }, [setUser]);

  const value: AuthContextValue = {
    user: authQuery.data ?? null,
    isLoading: authQuery.isLoading,
    error: authQuery.error instanceof Error ? authQuery.error : null,
    login,
    register,
    logout,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}

export function preventInvalidSubmit(event: FormEvent<HTMLFormElement>): boolean {
  const form = event.currentTarget;
  if (!form.checkValidity()) {
    form.reportValidity();
    return false;
  }
  return true;
}
