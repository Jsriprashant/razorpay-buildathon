import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatDistanceToNow } from "date-fns";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { NotificationsOut } from "@/types";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data } = useQuery<NotificationsOut>({
    queryKey: ["notifications"],
    queryFn: () => api.get<NotificationsOut>("/notifications"),
    refetchInterval: 30_000,
  });

  const markRead = useMutation({
    mutationFn: (notification_id?: number) => api.post<NotificationsOut>("/notifications/read", { notification_id }),
    onSuccess: (result) => {
      queryClient.setQueryData(["notifications"], result);
    },
  });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const items = data?.items ?? [];
  const unread = data?.unread_count ?? 0;

  return (
    <div className="relative" ref={containerRef}>
      <Button variant="ghost" size="icon" title="Notifications" onClick={() => setOpen((o) => !o)}>
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <Badge
            variant="destructive"
            className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px]"
          >
            {unread > 9 ? "9+" : unread}
          </Badge>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 rounded-lg border border-border bg-card shadow-lg">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-medium text-foreground">Notifications</span>
            {unread > 0 && (
              <Button variant="ghost" size="sm" className="h-auto px-2 py-1 text-xs" onClick={() => markRead.mutate(undefined)}>
                Mark all read
              </Button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto">
            {items.length === 0 && (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">No notifications yet.</p>
            )}
            {items.map((n) => (
              <button
                key={n.id}
                onClick={() => {
                  if (!n.read_at) markRead.mutate(n.id);
                  setOpen(false);
                  if (n.link) navigate(n.link);
                }}
                className={`block w-full border-b border-border px-3 py-2 text-left text-sm last:border-b-0 hover:bg-accent ${
                  n.read_at ? "text-muted-foreground" : "font-medium text-foreground"
                }`}
              >
                <p>{n.message}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
