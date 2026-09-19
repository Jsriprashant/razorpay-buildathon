import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { DemoPanel } from "@/components/layout/DemoPanel";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";

export function Topbar() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function handleLogout() {
    await api.post("/auth/logout");
    queryClient.clear();
    refresh();
    navigate("/login");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-card px-4">
      <div className="flex items-center gap-3 md:hidden">
        <span className="text-base font-bold tracking-tight text-foreground">HeadcountHQ</span>
      </div>
      <div className="flex flex-1 items-center justify-end gap-3">
        <DemoPanel />
        <NotificationBell />
        {user && (
          <div className="flex items-center gap-2">
            <div className="text-right">
              <p className="text-sm font-medium leading-none text-foreground">{user.name}</p>
              <p className="text-xs text-muted-foreground">{user.team_name ?? "All teams"}</p>
            </div>
            <Badge variant="secondary">{user.role}</Badge>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
