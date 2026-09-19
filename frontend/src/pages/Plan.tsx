import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PlanLine, PlanOut, Settings } from "@/types";

interface EditableLine {
  month_start: string;
  planned_fte_hc: string;
  planned_vendor_hc: string;
  planned_budget_cents: string;
}

function toEditable(lines: PlanLine[]): EditableLine[] {
  return lines.map((l) => ({
    month_start: l.month_start,
    planned_fte_hc: String(l.planned_fte_hc),
    planned_vendor_hc: String(l.planned_vendor_hc),
    planned_budget_cents: (l.planned_budget_cents / 100).toFixed(2),
  }));
}

export default function Plan() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [rows, setRows] = useState<EditableLine[] | null>(null);
  const [saved, setSaved] = useState(false);

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data, isLoading } = useQuery<PlanOut>({ queryKey: ["plan"], queryFn: () => api.get<PlanOut>("/plan") });

  useEffect(() => {
    if (data) setRows(toEditable(data.lines));
  }, [data]);

  const mutation = useMutation({
    mutationFn: (lines: EditableLine[]) =>
      api.put<PlanOut>("/plan", {
        lines: lines.map((l) => ({
          month_start: l.month_start,
          planned_fte_hc: Number(l.planned_fte_hc) || 0,
          planned_vendor_hc: Number(l.planned_vendor_hc) || 0,
          planned_budget_cents: Math.round((Number(l.planned_budget_cents) || 0) * 100),
        })),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["plan"], updated);
      queryClient.invalidateQueries({ queryKey: ["kpis"] });
      queryClient.invalidateQueries({ queryKey: ["forecast"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const canEdit = user?.role === "HR" || user?.role === "MANAGER";

  function updateRow(index: number, field: keyof EditableLine, value: string) {
    setRows((prev) => {
      if (!prev) return prev;
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  const totalBudget = rows?.reduce((sum, r) => sum + (Number(r.planned_budget_cents) || 0), 0) ?? 0;

  return (
    <div>
      <PageHeader
        title="Plan"
        description="This fiscal year's headcount and budget plan, by month."
        actions={
          canEdit && (
            <Button onClick={() => rows && mutation.mutate(rows)} disabled={mutation.isPending || !rows}>
              {mutation.isPending ? "Saving…" : "Save plan"}
            </Button>
          )
        }
      />

      {isLoading && <Skeleton className="h-96 w-full" />}

      {!isLoading && rows && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 pr-4">Month</th>
                  <th className="pb-2 pr-4">Planned FTE HC</th>
                  <th className="pb-2 pr-4">Planned vendor HC</th>
                  <th className="pb-2 pr-4">Planned budget ({currency})</th>
                  <th className="pb-2 pr-4"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={row.month_start} className="border-b border-border/60">
                    <td className="py-2 pr-4 font-medium">{row.month_start}</td>
                    <td className="py-2 pr-4">
                      <Input
                        className="h-8 w-24"
                        type="number"
                        min="0"
                        disabled={!canEdit}
                        value={row.planned_fte_hc}
                        onChange={(e) => updateRow(i, "planned_fte_hc", e.target.value)}
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <Input
                        className="h-8 w-24"
                        type="number"
                        min="0"
                        disabled={!canEdit}
                        value={row.planned_vendor_hc}
                        onChange={(e) => updateRow(i, "planned_vendor_hc", e.target.value)}
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <Input
                        className="h-8 w-32"
                        type="number"
                        min="0"
                        step="0.01"
                        disabled={!canEdit}
                        value={row.planned_budget_cents}
                        onChange={(e) => updateRow(i, "planned_budget_cents", e.target.value)}
                      />
                    </td>
                    <td className="py-2 pr-4">
                      <Link
                        to={`/requests/new?type=FTE&target_start_date=${row.month_start}&quantity=1`}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        Request headcount
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td className="pt-3 pr-4 font-medium">Fiscal year total</td>
                  <td colSpan={2} />
                  <td className="pt-3 pr-4 font-medium">{(totalBudget / 100).toLocaleString(undefined, { style: "currency", currency })}</td>
                </tr>
              </tfoot>
            </table>
            {saved && <p className="mt-3 text-sm text-success">Plan saved.</p>}
            {mutation.isError && <p className="mt-3 text-sm text-destructive">Could not save the plan.</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
