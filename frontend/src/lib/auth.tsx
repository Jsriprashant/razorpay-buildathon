import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import type { CurrentUser } from "@/types";

interface AuthContextValue {
  user: CurrentUser | null;
  isLoading: boolean;
  refresh: () => void;
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<CurrentUser | null>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await api.get<CurrentUser>("/auth/me");
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
  });

  const refresh = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
  }, [queryClient]);

  const value = React.useMemo(() => ({ user: data ?? null, isLoading, refresh }), [data, isLoading, refresh]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
