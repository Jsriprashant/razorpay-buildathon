import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import type { Application, ApplicationStatus } from "@/types";

const COLUMNS: { status: ApplicationStatus; title: string }[] = [
  { status: "NEW", title: "New" },
  { status: "SHORTLISTED", title: "Shortlisted" },
  { status: "HIRED", title: "Hired" },
  { status: "REJECTED", title: "Rejected" },
];

export default function HrApplications() {
  const queryClient = useQueryClient();
  const [hireTarget, setHireTarget] = useState<Application | null>(null);
  const [hireDate, setHireDate] = useState("");
  const [salary, setSalary] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");

  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());

  const { data, isLoading, isError } = useQuery<Application[]>({
    queryKey: ["hr-applications", params.toString()],
    queryFn: () => api.get<Application[]>(`/hr/applications?${params.toString()}`),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["hr-applications"] });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ApplicationStatus }) =>
      api.post(`/hr/applications/${id}/status`, { status }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not update this application."),
  });

  const hireMutation = useMutation({
    mutationFn: () =>
      api.post(`/hr/applications/${hireTarget!.id}/hire`, {
        hire_date: hireDate,
        annual_salary_cents: Math.round((Number(salary) || 0) * 100),
      }),
    onSuccess: () => {
      setHireTarget(null);
      setHireDate("");
      setSalary("");
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not hire this applicant."),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Applications" description="Review applicants for open postings and hire when ready." />

      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border/70 bg-card p-3 shadow-card">
        <Input placeholder="Search name or email…" className="h-10 w-64 bg-background" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {error && <p className="rounded-xl bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</p>}

      {isLoading && <Skeleton className="h-64 w-full" />}

      {isError && !isLoading && (
        <p className="text-sm text-destructive">Could not load applications. Please try again.</p>
      )}

      {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No applications yet" />}

      {!isLoading && data && data.length > 0 && (
        <div className="grid gap-4 md:grid-cols-4">
          {COLUMNS.map((col) => (
            <div key={col.status} className="flex min-h-48 flex-col gap-3 rounded-2xl bg-muted/40 p-3">
              <p className="px-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{col.title}</p>
              {data
                .filter((a) => a.status === col.status)
                .map((a) => (
                  <Card key={a.id} className="transition-shadow hover:shadow-card-hover">
                    <CardContent className="flex flex-col gap-2 pt-4">
                      <p className="font-medium">{a.name}</p>
                      <p className="text-xs text-muted-foreground">{a.posting_title}</p>
                      <p className="text-xs text-muted-foreground">{a.email}</p>
                      {a.note && <p className="text-xs">{a.note}</p>}
                      {col.status !== "HIRED" && col.status !== "REJECTED" && (
                        <div className="flex flex-wrap gap-1.5 pt-1">
                          {col.status === "NEW" && (
                            <Button size="sm" variant="outline" onClick={() => statusMutation.mutate({ id: a.id, status: "SHORTLISTED" })}>
                              Shortlist
                            </Button>
                          )}
                          <Button
                            size="sm"
                            onClick={() => {
                              setHireTarget(a);
                              setSalary(a.suggested_annual_salary_cents ? (a.suggested_annual_salary_cents / 100).toFixed(2) : "");
                            }}
                          >
                            Hire
                          </Button>
                          <Button size="sm" variant="destructive" onClick={() => statusMutation.mutate({ id: a.id, status: "REJECTED" })}>
                            Reject
                          </Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
            </div>
          ))}
        </div>
      )}

      {hireTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-sm">
            <CardContent className="flex flex-col gap-4 pt-6">
              <div>
                <h2 className="text-lg font-medium">Hire {hireTarget.name}</h2>
                <p className="text-sm text-muted-foreground">This fills the next open position for this posting.</p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="hire_date">Hire date</Label>
                <Input id="hire_date" type="date" value={hireDate} onChange={(e) => setHireDate(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="hire_salary">Annual salary</Label>
                <Input
                  id="hire_salary"
                  type="number"
                  min="0"
                  step="0.01"
                  value={salary}
                  onChange={(e) => setSalary(e.target.value)}
                  required
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex items-center justify-end gap-2">
                <Button variant="outline" onClick={() => { setHireTarget(null); setError(null); }}>
                  Cancel
                </Button>
                <Button onClick={() => { setError(null); hireMutation.mutate(); }} disabled={hireMutation.isPending || !hireDate || !salary}>
                  {hireMutation.isPending ? "Hiring…" : "Confirm hire"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
