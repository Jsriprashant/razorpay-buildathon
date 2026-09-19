import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Area, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import type { ForecastOut, Settings, WhatIfOut } from "@/types";

export default function Forecast() {
  const navigate = useNavigate();
  const [showDisclosure, setShowDisclosure] = useState(false);
  const [whatIf, setWhatIf] = useState({
    hiring_delay_months: 0,
    attrition_pct_override: "",
    hiring_freeze_from_month: "",
    extra_hires: 0,
    extra_hires_type: "FTE" as "FTE" | "VENDOR",
    extra_hires_start_month: "",
    extra_hires_unit_cost_cents: "",
  });

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data, isLoading } = useQuery<ForecastOut>({ queryKey: ["forecast"], queryFn: () => api.get<ForecastOut>("/forecast") });

  const whatIfMutation = useMutation({
    mutationFn: () =>
      api.post<WhatIfOut>("/forecast/what-if", {
        hiring_delay_months: whatIf.hiring_delay_months,
        attrition_pct_override: whatIf.attrition_pct_override === "" ? null : Number(whatIf.attrition_pct_override),
        hiring_freeze_from_month: whatIf.hiring_freeze_from_month === "" ? null : `${whatIf.hiring_freeze_from_month}-01`,
        extra_hires: whatIf.extra_hires,
        extra_hires_type: whatIf.extra_hires_type,
        extra_hires_start_month: whatIf.extra_hires_start_month === "" ? null : `${whatIf.extra_hires_start_month}-01`,
        extra_hires_unit_cost_cents:
          whatIf.extra_hires_unit_cost_cents === "" ? null : Math.round(Number(whatIf.extra_hires_unit_cost_cents) * 100),
      }),
  });

  function createRequest(prefill: Record<string, unknown>) {
    const params = new URLSearchParams();
    Object.entries(prefill).forEach(([k, v]) => {
      if (v !== null && v !== undefined) params.set(k, String(v));
    });
    navigate(`/requests/new?${params.toString()}`);
  }

  const chartData = data?.months.map((m) => ({
    month: m.month_start.slice(0, 7),
    Plan: m.plan_fte_hc,
    Projected: m.projected_fte_hc,
    "With suggestions": m.with_suggestions_fte_hc,
  }));

  const costChartData = data?.months.map((m) => ({
    month: m.month_start.slice(0, 7),
    "Plan cost": m.plan_cost_cents / 100,
    "No action": m.no_action_cost_cents / 100,
    "With suggestions": m.with_suggestions_cost_cents / 100,
  }));

  return (
    <div>
      <PageHeader
        title="Forecast"
        description="Where headcount is headed if nothing changes, and what to request to stay on plan."
        actions={
          <Button variant="outline" onClick={() => setShowDisclosure((v) => !v)}>
            How is this calculated?
          </Button>
        }
      />

      {showDisclosure && (
        <Card className="mb-6 border-primary/15 bg-accent/30">
          <CardContent className="whitespace-pre-line pt-6 text-sm text-muted-foreground">{data?.disclosure}</CardContent>
        </Card>
      )}

      {isLoading && <Skeleton className="h-96 w-full rounded-2xl" />}

      {!isLoading && data && data.months.length === 0 && (
        <EmptyState
          title="No future months in this fiscal year"
          description="The forecast projects months remaining in the current fiscal year — none remain."
        />
      )}

      {!isLoading && data && data.months.length > 0 && (
        <>
          <Card className="mb-6 shadow-card-hover">
            <CardHeader>
              <CardTitle>Projected FTE headcount vs. plan</CardTitle>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="forecastFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.22} />
                      <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis
                    allowDecimals={false}
                    width={44}
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip contentStyle={{ borderRadius: 16, border: "1px solid hsl(var(--border))", boxShadow: "0 12px 32px -8px rgb(30 27 75 / .18)", fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area type="monotone" dataKey="Projected" fill="url(#forecastFill)" stroke="none" />
                  <Line type="monotone" dataKey="Plan" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="Projected" stroke="hsl(var(--destructive))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="With suggestions" stroke="hsl(var(--success))" strokeDasharray="5 5" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="mb-6 shadow-card-hover">
            <CardHeader>
              <CardTitle>Cost scenarios</CardTitle>
            </CardHeader>
            <CardContent className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={costChartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis
                    tickFormatter={(v) => formatCents(v * 100, currency)}
                    width={76}
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip formatter={(v) => formatCents(Number(v) * 100, currency)} contentStyle={{ borderRadius: 16, border: "1px solid hsl(var(--border))", boxShadow: "0 12px 32px -8px rgb(30 27 75 / .18)", fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Line type="monotone" dataKey="Plan cost" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="No action" stroke="hsl(var(--destructive))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="With suggestions" stroke="hsl(var(--success))" strokeDasharray="5 5" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

           <Card className="mb-6 shadow-card-hover">
            <CardHeader>
              <CardTitle>Suggestions</CardTitle>
            </CardHeader>
            <CardContent>
              {data.suggestions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No gaps between plan and projection — nothing to request.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                     <tr className="border-b border-border text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                      <th className="pb-2 pr-4">Type</th>
                      <th className="pb-2 pr-4">Quantity</th>
                      <th className="pb-2 pr-4">Start</th>
                      <th className="pb-2 pr-4">Request by</th>
                      <th className="pb-2 pr-4">Est. unit cost</th>
                      <th className="pb-2 pr-4" />
                    </tr>
                  </thead>
                  <tbody>
                    {data.suggestions.map((s, i) => (
                       <tr key={i} className="border-b border-border/60 transition-colors hover:bg-accent/40">
                        <td className="py-2 pr-4">
                          <Badge variant="outline">{s.type}</Badge>
                        </td>
                        <td className="py-2 pr-4">{s.quantity}</td>
                        <td className="py-2 pr-4">{s.start}</td>
                        <td className="py-2 pr-4">
                          {s.request_by}
                          {s.urgent && (
                            <Badge variant="destructive" className="ml-2">
                              Urgent
                            </Badge>
                          )}
                        </td>
                        <td className="py-2 pr-4">{s.unit_cost_cents ? formatCents(s.unit_cost_cents, currency) : "—"}</td>
                        <td className="py-2 pr-4">
                          <Button size="sm" onClick={() => createRequest(s.request_prefill)}>
                            Create request
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContent>
          </Card>

           <Card className="shadow-card-hover">
            <CardHeader>
              <CardTitle>What-if</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="flex flex-col gap-1.5">
                  <Label>Hiring delay (whole months)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="12"
                    value={whatIf.hiring_delay_months}
                    onChange={(e) => setWhatIf({ ...whatIf, hiring_delay_months: Number(e.target.value) })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Attrition % override</Label>
                  <Input
                    type="number"
                    step="0.01"
                    placeholder={String(settings?.attrition_pct_monthly ?? 0)}
                    value={whatIf.attrition_pct_override}
                    onChange={(e) => setWhatIf({ ...whatIf, attrition_pct_override: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Hiring freeze from month</Label>
                  <Input
                    type="month"
                    value={whatIf.hiring_freeze_from_month}
                    onChange={(e) => setWhatIf({ ...whatIf, hiring_freeze_from_month: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Extra hires</Label>
                  <Input
                    type="number"
                    min="0"
                    value={whatIf.extra_hires}
                    onChange={(e) => setWhatIf({ ...whatIf, extra_hires: Number(e.target.value) })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Extra hires type</Label>
                  <select
                     className="h-10 rounded-xl border border-input bg-background px-3 text-sm"
                    value={whatIf.extra_hires_type}
                    onChange={(e) => setWhatIf({ ...whatIf, extra_hires_type: e.target.value as "FTE" | "VENDOR" })}
                  >
                    <option value="FTE">FTE</option>
                    <option value="VENDOR">Vendor</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Extra hires start month</Label>
                  <Input
                    type="month"
                    value={whatIf.extra_hires_start_month}
                    onChange={(e) => setWhatIf({ ...whatIf, extra_hires_start_month: e.target.value })}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label>Extra hires unit cost override</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="team average"
                    value={whatIf.extra_hires_unit_cost_cents}
                    onChange={(e) => setWhatIf({ ...whatIf, extra_hires_unit_cost_cents: e.target.value })}
                  />
                </div>
              </div>
              <Button onClick={() => whatIfMutation.mutate()} disabled={whatIfMutation.isPending}>
                {whatIfMutation.isPending ? "Running…" : "Run what-if"}
              </Button>

              {whatIfMutation.data && (
                <>
                  <table className="mt-4 w-full text-sm">
                    <thead>
                       <tr className="border-b border-border text-left text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                        <th className="pb-2 pr-4">Month</th>
                        <th className="pb-2 pr-4">Baseline FTE / vendor</th>
                        <th className="pb-2 pr-4">What-if FTE / vendor</th>
                        <th className="pb-2 pr-4">Delta cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {whatIfMutation.data.months.map((m) => (
                        <tr key={m.month_start} className="border-b border-border/60">
                          <td className="py-2 pr-4">{m.month_start.slice(0, 7)}</td>
                          <td className="py-2 pr-4">
                            {m.baseline_fte_hc} / {m.baseline_vendor_hc}
                          </td>
                          <td className="py-2 pr-4">
                            {m.whatif_fte_hc} / {m.whatif_vendor_hc}
                          </td>
                          <td className={`py-2 pr-4 ${m.delta_cost_cents > 0 ? "text-destructive" : "text-success"}`}>
                            {formatCents(m.delta_cost_cents, currency)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <div className="mt-4">
                    <h3 className="mb-2 text-sm font-semibold">Suggestions under this scenario</h3>
                    {whatIfMutation.data.suggestions.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No gaps between plan and this scenario's projection.</p>
                    ) : (
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                            <th className="pb-2 pr-4">Type</th>
                            <th className="pb-2 pr-4">Quantity</th>
                            <th className="pb-2 pr-4">Start</th>
                            <th className="pb-2 pr-4">Request by</th>
                          </tr>
                        </thead>
                        <tbody>
                          {whatIfMutation.data.suggestions.map((s, i) => (
                            <tr key={i} className="border-b border-border/60">
                              <td className="py-2 pr-4">
                                <Badge variant="outline">{s.type}</Badge>
                              </td>
                              <td className="py-2 pr-4">{s.quantity}</td>
                              <td className="py-2 pr-4">{s.start}</td>
                              <td className="py-2 pr-4">
                                {s.request_by}
                                {s.urgent && (
                                  <Badge variant="destructive" className="ml-2">
                                    Urgent
                                  </Badge>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
