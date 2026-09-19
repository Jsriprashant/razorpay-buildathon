import { useQuery } from "@tanstack/react-query";
import { format } from "date-fns";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { parseDateOnly } from "@/lib/dates";
import type { Cycle, Settings } from "@/types";

export default function History() {
  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data, isLoading, isError } = useQuery<Cycle[]>({
    queryKey: ["cycles"],
    queryFn: () => api.get<Cycle[]>("/cycles"),
  });

  return (
    <div>
      <PageHeader title="History" description="Closed cycles: the roster snapshot and plan-vs-actual result recorded when each month rolled over." />

      {isLoading && <Skeleton className="h-64 w-full rounded-2xl" />}

      {isError && !isLoading && <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-5 text-sm text-destructive">Could not load cycle history. Please try again.</div>}

      {!isLoading && !isError && (!data || data.length === 0) && (
        <EmptyState
          title="No closed cycles yet"
          description="Once a month rolls over, its snapshot and plan-vs-actual result will show up here."
        />
      )}

      {!isLoading && data && data.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  <th className="pb-2 pr-4">Month</th>
                  <th className="pb-2 pr-4">Plan FTE / Actual</th>
                  <th className="pb-2 pr-4">Plan Vendor / Actual</th>
                  <th className="pb-2 pr-4">Plan budget</th>
                  <th className="pb-2 pr-4">Actual cost</th>
                  <th className="pb-2 pr-4">Variance</th>
                  <th className="pb-2 pr-4">Closed</th>
                </tr>
              </thead>
              <tbody>
                {data.map((cycle) => {
                  const s = cycle.summary;
                  const variance = s ? s.actual_cost_cents - s.plan_budget_cents : 0;
                  return (
                    <tr key={cycle.id} className="border-b border-border transition-colors last:border-b-0 hover:bg-accent/40">
                      <td className="py-2 pr-4 font-medium text-foreground">
                        {format(parseDateOnly(cycle.month_start), "MMMM yyyy")}
                      </td>
                      <td className="py-2 pr-4">
                        {s ? `${s.plan_fte_hc} / ${s.fte_hc}` : "—"}
                      </td>
                      <td className="py-2 pr-4">
                        {s ? `${s.plan_vendor_hc} / ${s.vendor_hc}` : "—"}
                      </td>
                      <td className="py-2 pr-4">{s ? formatCents(s.plan_budget_cents, currency) : "—"}</td>
                      <td className="py-2 pr-4">{s ? formatCents(s.actual_cost_cents, currency) : "—"}</td>
                      <td className={`py-2 pr-4 ${variance > 0 ? "text-destructive" : "text-success"}`}>
                        {s ? `${variance > 0 ? "+" : ""}${formatCents(variance, currency)}` : "—"}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {cycle.closed_at ? format(parseDateOnly(cycle.closed_at), "MMM d, yyyy") : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
