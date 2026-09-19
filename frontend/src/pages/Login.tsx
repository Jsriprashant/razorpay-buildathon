import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
    <div className="flex min-h-screen flex-col">
      <DemoBanner />
      <div className="flex flex-1 items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl font-semibold text-foreground">Sign in to HeadcountHQ</CardTitle>
            <p className="text-sm text-muted-foreground">Pick a demo user to explore the app as that role.</p>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {isLoading &&
              Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
            {isError && <p className="text-sm text-destructive">Could not load demo users. Is the backend running?</p>}
            {users?.map((user) => (
              <button
                key={user.id}
                onClick={() => handleLogin(user)}
                disabled={loggingInId !== null}
                className="flex items-center justify-between rounded-md border border-border px-4 py-3 text-left transition-colors hover:bg-accent disabled:opacity-60"
              >
                <div>
                  <p className="text-sm font-medium text-foreground">{user.name}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
                <Badge variant="secondary">{user.role.replace("_", " ")}</Badge>
              </button>
            ))}
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button variant="ghost" size="sm" disabled className="mt-2 self-start">
              {loggingInId !== null ? "Signing in…" : null}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
