import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { parseDateOnly } from "@/lib/dates";
import type { CycleCurrentOut, RolloverOut } from "@/types";

const REMINDED_KEY = "hchq:rollover-reminded-cycle-id";

/**
 * Checked on every manager page load (Section: "on every manager page
 * load"). A blocking modal offers to roll the previous cycle over; "Remind
 * me later" swaps it for a persistent, non-blocking banner instead of
 * nagging on every navigation — the old cycle stays fully workable either
 * way, this is purely about starting the next one.
 */
export function RolloverGate() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManager = user?.role === "MANAGER";

  const { data } = useQuery<CycleCurrentOut>({
    queryKey: ["cycles", "current"],
    queryFn: () => api.get<CycleCurrentOut>("/cycles/current"),
    enabled: isManager,
  });

  const cycleId = data?.cycle.id;

  useEffect(() => {
    if (cycleId === undefined) return;
    setDismissed(window.localStorage.getItem(REMINDED_KEY) === String(cycleId));
  }, [cycleId]);

  const rolloverMutation = useMutation({
    mutationFn: () => api.post<RolloverOut>("/cycles/rollover"),
    onSuccess: () => {
      setError(null);
      window.localStorage.removeItem(REMINDED_KEY);
      queryClient.invalidateQueries();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not start the new cycle."),
  });

  if (!isManager || !data?.needs_rollover) return null;

  const label = format(parseDateOnly(data.cycle.month_start), "MMMM yyyy");

  function remindLater() {
    if (cycleId !== undefined) window.localStorage.setItem(REMINDED_KEY, String(cycleId));
    setDismissed(true);
  }

  if (dismissed) {
    return (
      <div className="flex items-center justify-between gap-3 border-b border-warning/40 bg-warning/10 px-4 py-2 text-sm">
        <div className="flex items-center gap-2 text-foreground">
          <Calendar className="h-4 w-4 text-warning" />
          <span>
            Your {label} cycle has ended. Roll over when you&apos;re ready to close it and start the new one.
          </span>
        </div>
        <Button size="sm" variant="outline" onClick={() => rolloverMutation.mutate()} disabled={rolloverMutation.isPending}>
          {rolloverMutation.isPending ? "Starting…" : "Start fresh cycle"}
        </Button>
      </div>
    );
  }

  return (
    <Dialog open={!dismissed} onOpenChange={(v) => !v && remindLater()}>
      <DialogContent hideClose>
        <DialogHeader>
          <DialogTitle>A new month has started</DialogTitle>
          <DialogDescription>
            Your {label} cycle has ended. Starting a fresh cycle snapshots your roster, records that month's actuals
            against its plan, and opens the new month for requests. Draft, submitted, and approved requests carry
            over unchanged.
          </DialogDescription>
        </DialogHeader>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button variant="outline" onClick={remindLater} disabled={rolloverMutation.isPending}>
            Remind me later
          </Button>
          <Button onClick={() => rolloverMutation.mutate()} disabled={rolloverMutation.isPending}>
            {rolloverMutation.isPending ? "Starting…" : "Start fresh cycle"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
