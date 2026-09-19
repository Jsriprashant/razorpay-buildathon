import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Circle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { CycleCurrentOut, ForecastOut, HiringRequest, PlanOut, ReconOut } from "@/types";

interface Step {
  key: string;
  label: string;
  done: boolean;
  to: string;
  cta: string;
}

/**
 * The "fresh checklist" a manager sees on Home: each step auto-ticks from
 * real data (never a page-visit flag) so it stays honest even if the user
 * navigates away and comes back. Disappears once every step is done.
 */
export function HomeChecklist() {
  const { data: plan } = useQuery<PlanOut>({ queryKey: ["plan"], queryFn: () => api.get<PlanOut>("/plan") });
  const { data: cycle } = useQuery<CycleCurrentOut>({
    queryKey: ["cycles", "current"],
    queryFn: () => api.get<CycleCurrentOut>("/cycles/current"),
  });
  const { data: recon } = useQuery<ReconOut>({ queryKey: ["recon"], queryFn: () => api.get<ReconOut>("/recon") });
  const { data: forecast } = useQuery<ForecastOut>({
    queryKey: ["forecast"],
    queryFn: () => api.get<ForecastOut>("/forecast"),
  });
  const { data: requests } = useQuery<HiringRequest[]>({
    queryKey: ["requests"],
    queryFn: () => api.get<HiringRequest[]>("/requests"),
  });

  if (!plan || !cycle || !recon || !forecast || !requests) return null;

  const steps: Step[] = [];
  if (!plan.has_plan) {
    steps.push({ key: "plan", label: "Set your plan", done: false, to: "/plan", cta: "Set plan" });
  }
  steps.push({
    key: "recon",
    label: "Review reconciliation",
    done: recon.unresolved_flag_count === 0,
    to: "/recon",
    cta: "Review recon",
  });
  steps.push({
    key: "forecast",
    label: "Review forecast",
    done: !forecast.suggestions.some((s) => s.urgent),
    to: "/forecast",
    cta: "Review forecast",
  });
  steps.push({
    key: "requests",
    label: "Raise requests for this cycle",
    done: requests.some((r) => r.cycle_id === cycle.cycle.id),
    to: "/requests/new",
    cta: "New request",
  });

  if (steps.every((s) => s.done)) return null;

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Get this cycle started</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {steps.map((step) => (
          <div key={step.key} className="flex items-center justify-between gap-3 rounded-xl border border-border px-3.5 py-2.5">
            <div className="flex items-center gap-2">
              {step.done ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-success" />
              ) : (
                <Circle className="h-5 w-5 shrink-0 text-muted-foreground" />
              )}
              <span className={step.done ? "text-sm text-muted-foreground line-through" : "text-sm font-medium text-foreground"}>
                {step.label}
              </span>
            </div>
            {!step.done && (
              <Button asChild size="sm" variant="outline">
                <Link to={step.to}>{step.cta}</Link>
              </Button>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
