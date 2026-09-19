import { useEffect, useMemo, useState } from "react";
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
    hiring_pct_adjustment: 0,
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
        hiring_pct_adjustment: whatIf.hiring_pct_adjustment,
        hiring_delay_months: whatIf.hiring_delay_months,
        attrition_pct_override:
          whatIf.attrition_pct_override === "" ? null : Number(whatIf.attrition_pct_override) / 100,
        hiring_freeze_from_month: whatIf.hiring_freeze_from_month === "" ? null : `${whatIf.hiring_freeze_from_month}-01`,
        extra_hires: whatIf.extra_hires,
        extra_hires_type: whatIf.extra_hires_type,
        extra_hires_start_month: whatIf.extra_hires_start_month === "" ? null : `${whatIf.extra_hires_start_month}-01`,
        extra_hires_unit_cost_cents:
          whatIf.extra_hires_unit_cost_cents === "" ? null : Math.round(Number(whatIf.extra_hires_unit_cost_cents) * 100),
      }),
  });

  useEffect(() => {
    if (settings && whatIf.attrition_pct_override === "") {
      setWhatIf((current) => ({
        ...current,
        attrition_pct_override: String(settings.attrition_pct_monthly * 100),
      }));
    }
  }, [settings, whatIf.attrition_pct_override]);

  useEffect(() => {
    if (!data || whatIf.attrition_pct_override === "") return;
    const timer = window.setTimeout(() => whatIfMutation.mutate(), 300);
    return () => window.clearTimeout(timer);
    // The individual primitive values make scenario changes explicit and
    // avoid rerunning because the mutation object itself changed identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    data,
    whatIf.hiring_pct_adjustment,
    whatIf.hiring_delay_months,
    whatIf.attrition_pct_override,
    whatIf.hiring_freeze_from_month,
    whatIf.extra_hires,
    whatIf.extra_hires_type,
    whatIf.extra_hires_start_month,
    whatIf.extra_hires_unit_cost_cents,
  ]);

  function createRequest(prefill: Record<string, unknown>) {
    const params = new URLSearchParams();
    Object.entries(prefill).forEach(([k, v]) => {
      if (v !== null && v !== undefined) params.set(k, String(v));
    });
    navigate(`/requests/new?${params.toString()}`);
  }

  const scenarioByMonth = useMemo(
    () => new Map(whatIfMutation.data?.months.map((month) => [month.month_start, month]) ?? []),
    [whatIfMutation.data],
  );

  const scenarioChanged =
    whatIf.hiring_pct_adjustment !== 0 ||
    Number(whatIf.attrition_pct_override) !== (settings?.attrition_pct_monthly ?? 0) * 100 ||
    whatIf.hiring_delay_months !== 0 ||
    whatIf.hiring_freeze_from_month !== "" ||
    whatIf.extra_hires !== 0;

  const chartData = data?.months.map((m) => {
    const scenario = scenarioByMonth.get(m.month_start);
    return {
      month: m.month_start.slice(0, 7),
      Plan: m.plan_fte_hc,
      "No action": m.projected_fte_hc,
      "With suggestions": m.with_suggestions_fte_hc,
      ...(scenarioChanged && scenario ? { "Your what-if": scenario.whatif_fte_hc } : {}),
    };
  });

  const costChartData = data?.months.map((m) => {
    const scenario = scenarioByMonth.get(m.month_start);
    return {
      month: m.month_start.slice(0, 7),
      "Plan cost": m.plan_cost_cents / 100,
      "No action": m.no_action_cost_cents / 100,
      "With suggestions": m.with_suggestions_cost_cents / 100,
      ...(scenarioChanged && scenario ? { "Your what-if": scenario.whatif_cost_cents / 100 } : {}),
    };
  });

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
          <Card className="mb-6 border-primary/15 bg-gradient-blue-soft shadow-card">
            <CardHeader>
              <CardTitle>What the three forecast lines mean</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 pt-0 sm:grid-cols-3">
              <div className="rounded-xl border border-border/70 bg-card/80 p-3">
                <p className="text-sm font-semibold text-primary">Plan</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  The approved monthly headcount and budget targets saved in your plan.
                </p>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/80 p-3">
                <p className="text-sm font-semibold text-destructive">No action</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  The expected result from the current roster, known exits, attrition, approved open positions, and vendor contracts.
                </p>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/80 p-3">
                <p className="text-sm font-semibold text-success">With suggestions</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  No action plus every gap-filling request listed below. It aims to match headcount, so it can exceed the budget plan.
                </p>
              </div>
            </CardContent>
          </Card>

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
                  <Area type="monotone" dataKey="No action" fill="url(#forecastFill)" stroke="none" />
                  <Line type="monotone" dataKey="Plan" stroke="hsl(var(--primary))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="No action" stroke="hsl(var(--destructive))" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="With suggestions" stroke="hsl(var(--success))" strokeDasharray="5 5" strokeWidth={2.5} dot={false} />
                  {scenarioChanged && (
                    <Line type="monotone" dataKey="Your what-if" stroke="hsl(var(--warning))" strokeWidth={3} dot={false} />
                  )}
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
                  {scenarioChanged && (
                    <Line type="monotone" dataKey="Your what-if" stroke="hsl(var(--warning))" strokeWidth={3} dot={false} />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="mb-6 shadow-card-hover">
            <CardHeader>
              <CardTitle>Suggestions</CardTitle>
               <p className="text-sm leading-5 text-muted-foreground">
                 Automatically detected from each month&apos;s plan minus its no-action projection. “Urgent” means the
                 request-by date has already passed after applying the configured lead time.
               </p>
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
                             <Badge
                               variant="destructive"
                               className="ml-2"
                               title="The recommended request-by date has already passed."
                             >
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
               <CardTitle>Live what-if scenario</CardTitle>
               <p className="text-sm leading-5 text-muted-foreground">
                 Move either slider and the amber “Your what-if” lines update automatically. This is a temporary
                 scenario—it does not change your saved plan or create requests.
               </p>
            </CardHeader>
            <CardContent>
               <div className="mb-6 grid gap-4 rounded-2xl border border-primary/15 bg-gradient-blue-soft p-4 sm:grid-cols-2">
                 <div>
                   <div className="mb-2 flex items-center justify-between gap-3">
                     <Label htmlFor="hiring-adjustment">Approved hiring pipeline</Label>
                     <span className="font-numeric rounded-full bg-card px-2.5 py-1 text-xs font-bold text-primary shadow-card">
                       {whatIf.hiring_pct_adjustment > 0 ? "+" : ""}
                       {whatIf.hiring_pct_adjustment}%
                     </span>
                   </div>
                   <input
                     id="hiring-adjustment"
                     type="range"
                     min="-100"
                     max="100"
                     step="10"
                     value={whatIf.hiring_pct_adjustment}
                     onChange={(e) => setWhatIf({ ...whatIf, hiring_pct_adjustment: Number(e.target.value) })}
                     className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
                   />
                   <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
                     <span>100% fewer</span>
                     <span>Current pipeline</span>
                     <span>100% more</span>
                   </div>
                   <p className="mt-2 text-xs leading-5 text-muted-foreground">
                     Scales approved open positions expected to land by each month.
                   </p>
                 </div>

                 <div>
                   <div className="mb-2 flex items-center justify-between gap-3">
                     <Label htmlFor="attrition-adjustment">Monthly attrition</Label>
                     <span className="font-numeric rounded-full bg-card px-2.5 py-1 text-xs font-bold text-primary shadow-card">
                       {Number(whatIf.attrition_pct_override).toFixed(1)}%
                     </span>
                   </div>
                   <input
                     id="attrition-adjustment"
                     type="range"
                     min="0"
                     max="10"
                     step="0.1"
                     value={whatIf.attrition_pct_override}
                     onChange={(e) => setWhatIf({ ...whatIf, attrition_pct_override: e.target.value })}
                     className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted accent-primary"
                   />
                   <div className="mt-1.5 flex justify-between text-[10px] text-muted-foreground">
                     <span>0%</span>
                     <span>Monthly employee attrition</span>
                     <span>10%</span>
                   </div>
                   <p className="mt-2 text-xs leading-5 text-muted-foreground">
                     Overrides the current setting of {((settings?.attrition_pct_monthly ?? 0) * 100).toFixed(1)}% per month.
                   </p>
                 </div>
               </div>

               <div className="mb-4">
                 <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Advanced scenario controls</p>
                 <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
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
              </div>
               <div className="flex items-center justify-between gap-3">
                 <p className="text-xs text-muted-foreground">
                   {whatIfMutation.isPending ? "Updating scenario…" : scenarioChanged ? "Scenario applied to both charts." : "Showing the baseline forecast."}
                 </p>
                 {scenarioChanged && (
                   <Button
                     variant="outline"
                     size="sm"
                     onClick={() =>
                       setWhatIf({
                         hiring_pct_adjustment: 0,
                         hiring_delay_months: 0,
                         attrition_pct_override: String((settings?.attrition_pct_monthly ?? 0) * 100),
                         hiring_freeze_from_month: "",
                         extra_hires: 0,
                         extra_hires_type: "FTE",
                         extra_hires_start_month: "",
                         extra_hires_unit_cost_cents: "",
                       })
                     }
                   >
                     Reset scenario
                   </Button>
                 )}
               </div>

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
