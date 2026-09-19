import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { parseDateOnly } from "@/lib/dates";
import type { Settings } from "@/types";

export function DemoPanel() {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  const advanceMutation = useMutation({
    mutationFn: () => api.post<Settings>("/demo/advance-month"),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not advance the clock."),
  });

  const resetMutation = useMutation({
    mutationFn: () => api.post<Settings>("/demo/reset"),
    onSuccess: () => {
      setError(null);
      setOpen(false);
      queryClient.clear();
      navigate("/home");
      window.location.reload();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not reset demo data."),
  });

  const demoToday = settings?.demo_today ? format(parseDateOnly(settings.demo_today), "MMMM d, yyyy") : null;

  return (
    <div className="relative" ref={containerRef}>
      <Button variant="outline" size="sm" className="gap-2" onClick={() => setOpen((o) => !o)}>
        <Settings2 className="h-4 w-4" />
        Demo panel
      </Button>

      {open && (
        <div className="absolute right-0 z-40 mt-2 w-72 rounded-lg border border-border bg-card p-3 shadow-lg">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Simulated date</p>
          <p className="mt-1 text-sm font-medium text-foreground">{demoToday ?? "Real clock"}</p>

          <div className="mt-3 flex flex-col gap-2">
            <Button size="sm" onClick={() => advanceMutation.mutate()} disabled={advanceMutation.isPending}>
              {advanceMutation.isPending ? "Advancing…" : "Advance to next month"}
            </Button>
            <Button
              size="sm"
              variant="destructive"
              disabled={resetMutation.isPending}
              onClick={() => {
                if (window.confirm("Reset all demo data back to the original seed? This cannot be undone.")) {
                  resetMutation.mutate();
                }
              }}
            >
              {resetMutation.isPending ? "Resetting…" : "Reset demo data"}
            </Button>
          </div>
          {error && <p className="mt-2 text-xs text-destructive">{error}</p>}
          <p className="mt-2 text-[11px] leading-snug text-muted-foreground">
            Advancing the clock does not close the current cycle by itself — the next page load will prompt you to
            roll over.
          </p>
        </div>
      )}
    </div>
  );
}
