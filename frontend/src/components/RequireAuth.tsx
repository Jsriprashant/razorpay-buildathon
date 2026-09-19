import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return <div className="flex h-screen items-center justify-center text-sm text-muted-foreground">Loading…</div>;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export function RequireRole({ role, children }: { role: "HR" | "MANAGER"; children: React.ReactNode }) {
  const { user } = useAuth();
  if (user && user.role !== role) {
    return <Navigate to="/home" replace />;
  }
  return <>{children}</>;
}
