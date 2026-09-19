import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { DemoUser } from "@/types";

export default function Login() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { refresh } = useAuth();
  const [loggingInId, setLoggingInId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: users, isLoading, isError } = useQuery<DemoUser[]>({
    queryKey: ["auth", "demo-users"],
    queryFn: () => api.get<DemoUser[]>("/auth/demo-users"),
  });

  async function handleLogin(user: DemoUser) {
    setError(null);
    setLoggingInId(user.id);
    try {
      await api.post("/auth/login", { user_id: user.id });
      queryClient.invalidateQueries({ queryKey: ["auth"] });
      refresh();
      navigate("/home");
    } catch {
      setError("Could not log in. Please try again.");
    } finally {
      setLoggingInId(null);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <DemoBanner />
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <span className="font-logotype text-3xl font-medium tracking-tight text-foreground">HeadcountHQ</span>
            <p className="mt-2 text-sm text-muted-foreground">Headcount planning, reconciliation and hiring in one place.</p>
          </div>
          <Card className="shadow-card-hover">
            <CardHeader>
              <CardTitle className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Sign in</CardTitle>
              <p className="text-sm text-foreground">Pick a demo user to explore the app as that role.</p>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              {isLoading &&
                Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
              {isError && <p className="text-sm text-destructive">Could not load demo users. Is the backend running?</p>}
              {users?.map((user) => {
                const initials = user.name
                  .split(" ")
                  .map((p) => p[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase();
                return (
                  <button
                    key={user.id}
                    onClick={() => handleLogin(user)}
                    disabled={loggingInId !== null}
                    className="flex items-center gap-3 rounded-xl border border-border px-4 py-3 text-left transition-all hover:border-primary/40 hover:bg-accent disabled:opacity-60"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {loggingInId === user.id ? "…" : initials}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                    </div>
                    <Badge variant="secondary">{user.role.replace("_", " ")}</Badge>
                  </button>
                );
              })}
              {error && <p className="text-sm text-destructive">{error}</p>}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
