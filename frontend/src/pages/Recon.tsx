import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import type { PositionMatch, ReconOut, Settings } from "@/types";

function monthInputValue(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export default function Recon() {
  const queryClient = useQueryClient();
  const [month, setMonth] = useState(() => monthInputValue(new Date()));

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data, isLoading } = useQuery<ReconOut>({
    queryKey: ["recon", month],
    queryFn: () => api.get<ReconOut>(`/recon?month=${month}-01`),
  });

  const resolveMutation = useMutation({
    mutationFn: (vars: { category: string; worker_pk: number | null; position_id: number | null }) =>
      api.post("/recon/resolve", { ...vars, period_month: `${month}-01` }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recon", month] }),
  });

  const bulkAcknowledgeMutation = useMutation({
    mutationFn: (items: { category: string; worker_pk: number | null; position_id: number | null }[]) =>
      api.post("/recon/resolve/bulk", { items: items.map((i) => ({ ...i, period_month: `${month}-01` })) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["recon", month] }),
  });

  const [linkingWorker, setLinkingWorker] = useState<number | null>(null);
  const [matches, setMatches] = useState<PositionMatch[]>([]);

  const linkMutation = useMutation({
    mutationFn: (vars: { worker_pk: number; position_id: number }) => api.post("/recon/link-position", vars),
    onSuccess: () => {
      setLinkingWorker(null);
      setMatches([]);
      queryClient.invalidateQueries({ queryKey: ["recon", month] });
    },
  });

  async function findMatches(workerPk: number, jobTitle: string, grade: string | null) {
    const params = new URLSearchParams({ job_title: jobTitle });
    if (grade) params.set("grade", grade);
    const found = await api.get<PositionMatch[]>(`/roster/workers/propose-match?${params.toString()}`);
    setLinkingWorker(workerPk);
    setMatches(found);
  }

  function allUnresolvedItems(): { category: string; worker_pk: number | null; position_id: number | null }[] {
    if (!data) return [];
    const items: { category: string; worker_pk: number | null; position_id: number | null }[] = [];
    for (const item of data.changes.new_hires) {
      if (item.flags.includes("UNPLANNED_HIRE") && !item.resolved) {
        items.push({ category: "UNPLANNED_HIRE", worker_pk: item.worker_pk, position_id: null });
      }
    }
    for (const p of data.requested_vs_actual.positions) {
      if (p.status === "OVERDUE" && !p.resolved) {
        items.push({ category: "REQUESTED_VS_ACTUAL", worker_pk: null, position_id: p.position_id });
      }
    }
    for (const h of data.requested_vs_actual.unplanned_hires) {
      if (!h.resolved) items.push({ category: "UNPLANNED_HIRE", worker_pk: h.worker_pk, position_id: null });
    }
    for (const r of data.plan_vs_actual.rows) {
      if (!r.is_closed && r.variance_cents !== 0 && !r.resolved) {
        items.push({ category: "PLAN_VARIANCE", worker_pk: null, position_id: null });
      }
    }
    return items;
  }

  return (
    <div>
      <PageHeader
        title="Reconciliation"
        description="What changed, what was requested vs. what happened, and plan vs. actual — by month."
        actions={<Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-auto" />}
      />

      {isLoading && <Skeleton className="h-96 w-full" />}

      {!isLoading && data && (
        <>
          {data.unresolved_flag_count > 0 && (
            <div className="mb-4 flex items-center justify-between rounded-md border border-warning/40 bg-warning/10 px-4 py-2 text-sm">
              <span>
                {data.unresolved_flag_count} unresolved flag{data.unresolved_flag_count !== 1 ? "s" : ""} this period.
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={bulkAcknowledgeMutation.isPending}
                onClick={() => bulkAcknowledgeMutation.mutate(allUnresolvedItems())}
              >
                Acknowledge all
              </Button>
            </div>
          )}

          {linkingWorker !== null && (
            <div className="mb-4 rounded-md border border-border bg-muted/40 px-4 py-3 text-sm">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium">Link to an open position</span>
                <Button size="sm" variant="ghost" onClick={() => { setLinkingWorker(null); setMatches([]); }}>
                  Cancel
                </Button>
              </div>
              {matches.length === 0 ? (
                <p className="text-muted-foreground">No open positions match this worker's title/grade.</p>
              ) : (
                <ul className="space-y-1">
                  {matches.map((m) => (
                    <li key={m.position_id} className="flex items-center justify-between">
                      <span>
                        {m.role_title} {m.grade && `(${m.grade})`} · target {m.target_start_date}
                      </span>
                      <Button
                        size="sm"
                        onClick={() => linkMutation.mutate({ worker_pk: linkingWorker, position_id: m.position_id })}
                        disabled={linkMutation.isPending}
                      >
                        Link
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <Tabs defaultValue="changes">
            <TabsList>
              <TabsTrigger value="changes">Changes since last month</TabsTrigger>
              <TabsTrigger value="requested">Requested vs. actual</TabsTrigger>
              <TabsTrigger value="plan">Plan vs. actual</TabsTrigger>
            </TabsList>

            <TabsContent value="changes">
              {data.changes.is_baseline ? (
                <EmptyState
                  title="This is the first snapshot period"
                  description="There's no prior month to diff against yet — changes will appear starting next month."
                />
              ) : (
                <Card>
                  <CardContent className="overflow-x-auto pt-6">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                          <th className="pb-2 pr-4">Worker</th>
                          <th className="pb-2 pr-4">Category</th>
                          <th className="pb-2 pr-4">Detail</th>
                          <th className="pb-2 pr-4">Flags</th>
                          <th className="pb-2 pr-4">Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...data.changes.new_hires, ...data.changes.exits, ...data.changes.changes].map((item, i) => (
                          <tr key={`${item.worker_id}-${i}`} className="border-b border-border/60">
                            <td className="py-2 pr-4">
                              {item.name} <span className="text-muted-foreground">({item.worker_id})</span>
                            </td>
                            <td className="py-2 pr-4">
                              <Badge variant={item.category === "EXIT" ? "secondary" : "outline"}>{item.category}</Badge>
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {item.category === "CHANGE" && (
                                <div className="space-y-0.5">
                                  {(item.before_grade !== null || item.after_grade !== null) && (
                                    <div>Grade: {item.before_grade ?? "—"} → {item.after_grade ?? "—"}</div>
                                  )}
                                  {(item.before_salary_cents !== null || item.after_salary_cents !== null) && (
                                    <div>
                                      Salary:{" "}
                                      {item.before_salary_cents !== null ? formatCents(item.before_salary_cents, currency) : "—"}{" "}
                                      → {item.after_salary_cents !== null ? formatCents(item.after_salary_cents, currency) : "—"}
                                    </div>
                                  )}
                                  {(item.before_title !== null || item.after_title !== null) && (
                                    <div>Title: {item.before_title ?? "—"} → {item.after_title ?? "—"}</div>
                                  )}
                                  {(item.before_manager !== null || item.after_manager !== null) && (
                                    <div>Manager: {item.before_manager ?? "—"} → {item.after_manager ?? "—"}</div>
                                  )}
                                </div>
                              )}
                              {item.category === "NEW_HIRE" && item.job_title}
                              {item.category === "EXIT" && item.job_title}
                            </td>
                            <td className="py-2 pr-4">
                              {item.flags.map((f) => (
                                <Badge key={f} variant="warning" className="mr-1">
                                  {f}
                                </Badge>
                              ))}
                            </td>
                            <td className="py-2 pr-4">
                              {item.flags.length > 0 && !item.resolved && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() =>
                                    resolveMutation.mutate({
                                      category: item.flags.includes("UNPLANNED_HIRE") ? "UNPLANNED_HIRE" : "CHANGE",
                                      worker_pk: item.worker_pk,
                                      position_id: null,
                                    })
                                  }
                                >
                                  Acknowledge
                                </Button>
                              )}
                              {item.category === "NEW_HIRE" && item.flags.includes("UNPLANNED_HIRE") && !item.resolved && item.job_title && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="ml-1"
                                  onClick={() => item.worker_pk && findMatches(item.worker_pk, item.job_title ?? "", null)}
                                >
                                  Link to position
                                </Button>
                              )}
                              {item.resolved && <Badge variant="success">Acknowledged</Badge>}
                            </td>
                          </tr>
                        ))}
                        {data.changes.new_hires.length + data.changes.exits.length + data.changes.changes.length === 0 && (
                          <tr>
                            <td colSpan={5} className="py-6 text-center text-muted-foreground">
                              No changes this period ({data.changes.unchanged_count} workers unchanged).
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="requested">
              <Card>
                <CardContent className="overflow-x-auto pt-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                        <th className="pb-2 pr-4">Role</th>
                        <th className="pb-2 pr-4">Target start</th>
                        <th className="pb-2 pr-4">Status</th>
                        <th className="pb-2 pr-4">Filled by</th>
                        <th className="pb-2 pr-4">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.requested_vs_actual.positions.map((p) => (
                        <tr key={p.position_id} className="border-b border-border/60">
                          <td className="py-2 pr-4">
                            {p.role_title} {p.grade && <span className="text-muted-foreground">({p.grade})</span>}
                          </td>
                          <td className="py-2 pr-4">{p.target_start_date}</td>
                          <td className="py-2 pr-4">
                            <Badge
                              variant={p.status === "FILLED" ? "success" : p.status === "OVERDUE" ? "destructive" : "outline"}
                            >
                              {p.status}
                              {p.status === "OVERDUE" && p.days_open ? ` · ${p.days_open}d` : ""}
                            </Badge>
                          </td>
                          <td className="py-2 pr-4">{p.filled_worker_id ?? "—"}</td>
                          <td className="py-2 pr-4">
                            {p.status === "OVERDUE" && !p.resolved && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  resolveMutation.mutate({
                                    category: "REQUESTED_VS_ACTUAL",
                                    worker_pk: null,
                                    position_id: p.position_id,
                                  })
                                }
                              >
                                Acknowledge
                              </Button>
                            )}
                            {p.resolved && <Badge variant="success">Acknowledged</Badge>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {data.requested_vs_actual.unplanned_hires.length > 0 && (
                    <div className="mt-6">
                      <h3 className="mb-2 text-sm font-semibold">Unplanned hires this period</h3>
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                            <th className="pb-2 pr-4">Worker</th>
                            <th className="pb-2 pr-4">Title</th>
                            <th className="pb-2 pr-4">Hire date</th>
                            <th className="pb-2 pr-4">Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.requested_vs_actual.unplanned_hires.map((h) => (
                            <tr key={h.worker_pk} className="border-b border-border/60">
                              <td className="py-2 pr-4">
                                {h.name} <span className="text-muted-foreground">({h.worker_id})</span>
                              </td>
                              <td className="py-2 pr-4">{h.job_title}</td>
                              <td className="py-2 pr-4">{h.hire_date}</td>
                              <td className="py-2 pr-4">
                                {!h.resolved && (
                                  <>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      onClick={() =>
                                        resolveMutation.mutate({
                                          category: "UNPLANNED_HIRE",
                                          worker_pk: h.worker_pk,
                                          position_id: null,
                                        })
                                      }
                                    >
                                      Acknowledge
                                    </Button>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="ml-1"
                                      onClick={() => findMatches(h.worker_pk, h.job_title, h.grade)}
                                    >
                                      Link to position
                                    </Button>
                                  </>
                                )}
                                {h.resolved && <Badge variant="success">Acknowledged</Badge>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="plan">
              <Card>
                <CardContent className="overflow-x-auto pt-6">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                        <th className="pb-2 pr-4">Month</th>
                        <th className="pb-2 pr-4">FTE plan/actual</th>
                        <th className="pb-2 pr-4">Vendor plan/actual</th>
                        <th className="pb-2 pr-4">Budget</th>
                        <th className="pb-2 pr-4">Actual cost</th>
                        <th className="pb-2 pr-4">Variance</th>
                        <th className="pb-2 pr-4">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.plan_vs_actual.rows.map((r) => (
                        <tr key={r.month_start} className="border-b border-border/60">
                          <td className="py-2 pr-4">
                            {r.month_start} {!r.is_closed && <Badge variant="outline">open</Badge>}
                          </td>
                          <td className="py-2 pr-4">
                            {r.plan_fte_hc} / {r.actual_fte_hc}
                          </td>
                          <td className="py-2 pr-4">
                            {r.plan_vendor_hc} / {r.actual_vendor_hc}
                          </td>
                          <td className="py-2 pr-4">{formatCents(r.plan_budget_cents, currency)}</td>
                          <td className="py-2 pr-4">{formatCents(r.actual_cost_cents, currency)}</td>
                          <td className={`py-2 pr-4 ${r.variance_cents > 0 ? "text-destructive" : "text-success"}`}>
                            {formatCents(r.variance_cents, currency)}
                          </td>
                          <td className="py-2 pr-4">
                            {!r.is_closed && r.variance_cents !== 0 && !r.resolved && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() =>
                                  resolveMutation.mutate({ category: "PLAN_VARIANCE", worker_pk: null, position_id: null })
                                }
                              >
                                Acknowledge
                              </Button>
                            )}
                            {r.resolved && <Badge variant="success">Acknowledged</Badge>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
