import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { useAuth } from "@/lib/auth";
import type { PositionMatch, Settings, Worker } from "@/types";

function monthInputValue(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

const emptyForm = {
  name: "",
  job_title: "",
  grade: "",
  hire_date: "",
  annual_salary_cents: "",
  location: "",
  cost_center: "",
};

export default function Roster() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [month, setMonth] = useState(() => monthInputValue(new Date()));
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<{ job_title: string; grade: string; annual_salary_cents: string }>({
    job_title: "",
    grade: "",
    annual_salary_cents: "",
  });
  const [exitingId, setExitingId] = useState<number | null>(null);
  const [exitForm, setExitForm] = useState({ last_working_day: "", reason: "" });

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data: workers, isLoading } = useQuery<Worker[]>({
    queryKey: ["roster", month],
    queryFn: () => api.get<Worker[]>(`/roster?month=${month}-01`),
  });

  const { data: matches } = useQuery<PositionMatch[]>({
    queryKey: ["roster", "propose-match", form.job_title, form.grade],
    queryFn: () =>
      api.get<PositionMatch[]>(
        `/roster/workers/propose-match?job_title=${encodeURIComponent(form.job_title)}${form.grade ? `&grade=${encodeURIComponent(form.grade)}` : ""}`,
      ),
    enabled: showAdd && form.job_title.trim().length > 1,
  });

  const addMutation = useMutation({
    mutationFn: (payload: { position_id?: number }) =>
      api.post<Worker>("/roster/workers", {
        name: form.name,
        job_title: form.job_title,
        grade: form.grade,
        hire_date: form.hire_date,
        annual_salary_cents: Math.round(Number(form.annual_salary_cents) * 100),
        location: form.location,
        cost_center: form.cost_center || undefined,
        position_id: payload.position_id,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roster"] });
      setShowAdd(false);
      setForm(emptyForm);
      setFormError(null);
    },
    onError: (err) => setFormError(err instanceof ApiError ? err.message : "Could not add worker."),
  });

  const updateMutation = useMutation({
    mutationFn: (id: number) =>
      api.patch<Worker>(`/roster/workers/${id}`, {
        job_title: editForm.job_title,
        grade: editForm.grade,
        annual_salary_cents: Math.round(Number(editForm.annual_salary_cents) * 100),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roster"] });
      setEditingId(null);
    },
  });

  const exitMutation = useMutation({
    mutationFn: (id: number) =>
      api.post<Worker>(`/roster/workers/${id}/exit`, {
        last_working_day: exitForm.last_working_day,
        reason: exitForm.reason,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roster"] });
      setExitingId(null);
      setExitForm({ last_working_day: "", reason: "" });
    },
  });

  const sortedWorkers = useMemo(
    () => [...(workers ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [workers],
  );

  const canEdit = user?.role === "HR" || user?.role === "MANAGER";

  return (
    <div>
      <PageHeader
        title="Roster"
        description="Everyone on the team, as of the selected month."
        actions={
          <>
            <Input type="month" value={month} onChange={(e) => setMonth(e.target.value)} className="w-auto" />
            {canEdit && <Button onClick={() => setShowAdd((v) => !v)}>{showAdd ? "Cancel" : "Add worker"}</Button>}
          </>
        }
      />

      {showAdd && (
        <Card className="mb-6">
          <CardContent className="pt-6">
            <form
              className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
              onSubmit={(e) => {
                e.preventDefault();
                const best = matches && matches.length > 0 ? matches[0] : undefined;
                addMutation.mutate({ position_id: best?.position_id });
              }}
            >
              <div className="flex flex-col gap-1.5">
                <Label>Name</Label>
                <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Job title</Label>
                <Input required value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Grade</Label>
                <Input required value={form.grade} onChange={(e) => setForm({ ...form, grade: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Hire date</Label>
                <Input required type="date" value={form.hire_date} onChange={(e) => setForm({ ...form, hire_date: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Annual salary</Label>
                <Input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.annual_salary_cents}
                  onChange={(e) => setForm({ ...form, annual_salary_cents: e.target.value })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Location</Label>
                <Input required value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Cost center (optional)</Label>
                <Input value={form.cost_center} onChange={(e) => setForm({ ...form, cost_center: e.target.value })} />
              </div>

              {matches && matches.length > 0 && (
                <div className="col-span-full rounded-md border border-success/40 bg-success/10 p-3 text-sm">
                  Matches an open position: <strong>{matches[0].role_title}</strong> (target start{" "}
                  {matches[0].target_start_date}). This hire will be linked to it automatically.
                </div>
              )}
              {matches && matches.length === 0 && form.job_title.trim().length > 1 && (
                <div className="col-span-full rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
                  No open approved position matches this title/grade — this hire will be flagged as unplanned in
                  reconciliation.
                </div>
              )}

              <div className="col-span-full flex items-center gap-3">
                <Button type="submit" disabled={addMutation.isPending}>
                  {addMutation.isPending ? "Adding…" : "Add to roster"}
                </Button>
                {formError && <span className="text-sm text-destructive">{formError}</span>}
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {isLoading && <Skeleton className="h-64 w-full" />}

      {!isLoading && sortedWorkers.length === 0 && (
        <EmptyState title="No one on the roster for this month" description="Add a worker to get started." />
      )}

      {!isLoading && sortedWorkers.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 pr-4">ID</th>
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Title</th>
                  <th className="pb-2 pr-4">Grade</th>
                  <th className="pb-2 pr-4">Manager</th>
                  <th className="pb-2 pr-4">Hire date</th>
                  <th className="pb-2 pr-4">Salary</th>
                  <th className="pb-2 pr-4">Status</th>
                  {canEdit && <th className="pb-2 pr-4">Actions</th>}
                </tr>
              </thead>
              <tbody>
                {sortedWorkers.map((w) => (
                  <tr key={w.id} className="border-b border-border/60 align-top">
                    <td className="py-2 pr-4 text-muted-foreground">{w.worker_id}</td>
                    <td className="py-2 pr-4 font-medium">{w.name}</td>
                    <td className="py-2 pr-4">
                      {editingId === w.id ? (
                        <Input
                          className="h-8"
                          value={editForm.job_title}
                          onChange={(e) => setEditForm({ ...editForm, job_title: e.target.value })}
                        />
                      ) : (
                        w.job_title
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {editingId === w.id ? (
                        <Input
                          className="h-8 w-16"
                          value={editForm.grade}
                          onChange={(e) => setEditForm({ ...editForm, grade: e.target.value })}
                        />
                      ) : (
                        w.grade
                      )}
                    </td>
                    <td className="py-2 pr-4">{w.manager_name ?? "—"}</td>
                    <td className="py-2 pr-4">{w.hire_date}</td>
                    <td className="py-2 pr-4">
                      {editingId === w.id ? (
                        <Input
                          className="h-8 w-28"
                          type="number"
                          step="0.01"
                          value={editForm.annual_salary_cents}
                          onChange={(e) => setEditForm({ ...editForm, annual_salary_cents: e.target.value })}
                        />
                      ) : (
                        formatCents(w.annual_salary_cents, currency)
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {w.termination_date ? (
                        <Badge variant="secondary">Exited {w.termination_date}</Badge>
                      ) : w.is_active ? (
                        <Badge variant="success">Active</Badge>
                      ) : (
                        <Badge variant="outline">Not started</Badge>
                      )}
                    </td>
                    {canEdit && (
                      <td className="py-2 pr-4">
                        {editingId === w.id ? (
                          <div className="flex gap-2">
                            <Button size="sm" onClick={() => updateMutation.mutate(w.id)} disabled={updateMutation.isPending}>
                              Save
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                              Cancel
                            </Button>
                          </div>
                        ) : exitingId === w.id ? (
                          <div className="flex flex-col gap-2">
                            <Input
                              className="h-8"
                              type="date"
                              value={exitForm.last_working_day}
                              onChange={(e) => setExitForm({ ...exitForm, last_working_day: e.target.value })}
                            />
                            <Input
                              className="h-8"
                              placeholder="Reason"
                              value={exitForm.reason}
                              onChange={(e) => setExitForm({ ...exitForm, reason: e.target.value })}
                            />
                            <div className="flex gap-2">
                              <Button size="sm" onClick={() => exitMutation.mutate(w.id)} disabled={exitMutation.isPending}>
                                Confirm exit
                              </Button>
                              <Button size="sm" variant="ghost" onClick={() => setExitingId(null)}>
                                Cancel
                              </Button>
                            </div>
                          </div>
                        ) : (
                          !w.termination_date && (
                            <div className="flex gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setEditingId(w.id);
                                  setEditForm({
                                    job_title: w.job_title,
                                    grade: w.grade,
                                    annual_salary_cents: (w.annual_salary_cents / 100).toFixed(2),
                                  });
                                }}
                              >
                                Edit
                              </Button>
                              <Button size="sm" variant="outline" onClick={() => setExitingId(w.id)}>
                                Exit
                              </Button>
                            </div>
                          )
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
