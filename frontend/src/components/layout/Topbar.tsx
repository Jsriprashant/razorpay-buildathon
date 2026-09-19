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

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((part) => part[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "";

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 lg:px-6">
      <div className="flex items-center gap-3 md:hidden">
        <span className="font-logotype text-lg font-medium tracking-tight text-foreground">HeadcountHQ</span>
      </div>
      <div className="hidden text-sm text-muted-foreground md:block">{user?.team_name ?? "All teams"}</div>
      <div className="flex flex-1 items-center justify-end gap-2">
        <DemoPanel />
        <NotificationBell />
        {/* Profile + logout live at the bottom of the sidebar on md+ screens; this is the mobile-only fallback. */}
        {user && (
          <div className="ml-1 flex items-center gap-3 rounded-full border border-border bg-background py-1 pl-1 pr-1.5 md:hidden">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-blue text-xs font-semibold text-white">
              {initials}
            </div>
            <div className="hidden text-left sm:block">
              <p className="text-sm font-medium leading-none text-foreground">{user.name}</p>
              <Badge variant="secondary" className="mt-1 px-1.5 py-0 text-[10px] leading-4">
                {user.role.replace("_", " ")}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" className="rounded-full" onClick={handleLogout}>
              Log out
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
