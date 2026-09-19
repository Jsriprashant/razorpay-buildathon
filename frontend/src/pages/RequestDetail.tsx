import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { useAuth } from "@/lib/auth";
import type { RequestDetail as RequestDetailType, Settings } from "@/types";

export default function RequestDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const { data: req, isLoading } = useQuery<RequestDetailType>({
    queryKey: ["requests", id],
    queryFn: () => api.get<RequestDetailType>(`/requests/${id}`),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["requests"] });
    queryClient.invalidateQueries({ queryKey: ["requests", id] });
  };

  const submitMutation = useMutation({
    mutationFn: (action: "submit" | "resubmit" | "cancel") => api.post(`/requests/${id}/${action}`),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Action failed."),
  });

  const hrCancelMutation = useMutation({
    mutationFn: () => api.post(`/hr/requests/${id}/cancel`, { note: "Cancelled by HR" }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Action failed."),
  });

  if (isLoading || !req) {
    return (
      <div>
        <PageHeader title="Request" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const isOwnerManager = user?.role === "MANAGER" && user.id === req.created_by;
  const canEdit = isOwnerManager && (req.status === "DRAFT" || req.status === "CHANGES_REQUESTED");
  const canSubmit = isOwnerManager && req.status === "DRAFT";
  const canResubmit = isOwnerManager && req.status === "CHANGES_REQUESTED";
  const canCancel = isOwnerManager && (req.status === "DRAFT" || req.status === "SUBMITTED");
  const canHrCancel = user?.role === "HR" && req.status === "APPROVED";

  return (
    <div>
      <PageHeader
        title={req.role_title}
        description={`${req.type} request · ${req.team_name ?? ""}`}
        actions={
          <div className="flex items-center gap-2">
            {canEdit && (
              <Button asChild variant="outline">
                <Link to={`/requests/new?edit=${req.id}`}>Edit</Link>
              </Button>
            )}
            {canSubmit && (
              <Button onClick={() => submitMutation.mutate("submit")} disabled={submitMutation.isPending}>
                Submit for approval
              </Button>
            )}
            {canResubmit && (
              <Button onClick={() => submitMutation.mutate("resubmit")} disabled={submitMutation.isPending}>
                Resubmit
              </Button>
            )}
            {canCancel && (
              <Button
                variant="destructive"
                onClick={() => submitMutation.mutate("cancel")}
                disabled={submitMutation.isPending}
              >
                Cancel
              </Button>
            )}
            {canHrCancel && (
              <Button variant="destructive" onClick={() => hrCancelMutation.mutate()} disabled={hrCancelMutation.isPending}>
                Cancel approved request
              </Button>
            )}
          </div>
        }
      />

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="flex flex-col gap-4 pt-6">
            <div className="flex items-center gap-2">
              <StatusBadge status={req.status} />
              {req.plan_fit && <StatusBadge status={req.plan_fit} />}
              {req.budget_fit && <StatusBadge status={req.budget_fit} />}
            </div>

            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <div>
                <dt className="text-xs uppercase text-muted-foreground">Quantity</dt>
                <dd>{req.quantity}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase text-muted-foreground">Target start</dt>
                <dd>{req.target_start_date}</dd>
              </div>
              {req.type === "FTE" ? (
                <>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Grade</dt>
                    <dd>{req.grade}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Annual salary</dt>
                    <dd>{req.annual_salary_cents ? formatCents(req.annual_salary_cents, currency) : "—"}</dd>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Vendor</dt>
                    <dd>{req.vendor_company_name}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Rate</dt>
                    <dd>
                      {req.hourly_rate_cents ? formatCents(req.hourly_rate_cents, currency) : "—"}/hr ·{" "}
                      {req.hours_per_month} hrs/mo
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">End date</dt>
                    <dd>{req.end_date}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted-foreground">Contract value</dt>
                    <dd>{req.contract_value_cents ? formatCents(req.contract_value_cents, currency) : "—"}</dd>
                  </div>
                </>
              )}
            </dl>

            {req.justification && (
              <div>
                <dt className="text-xs uppercase text-muted-foreground">Justification</dt>
                <dd className="mt-1 text-sm">{req.justification}</dd>
              </div>
            )}

            {req.decision_note && (
              <div className="rounded-md border border-border bg-muted/40 px-4 py-3 text-sm">
                <span className="font-medium">HR note: </span>
                {req.decision_note}
              </div>
            )}

            {req.type === "FTE" && req.posting_slug && (
              <div className="rounded-md border border-border px-4 py-3 text-sm">
                <span className="text-muted-foreground">Job posting: </span>
                <Link to={`/careers/${req.posting_slug}`} className="font-medium hover:underline" target="_blank">
                  /careers/{req.posting_slug}
                </Link>
                {req.posting_status && <StatusBadge status={req.posting_status} className="ml-2" />}
              </div>
            )}

            {req.type === "FTE" && req.positions.length > 0 && (
              <div>
                <p className="mb-2 text-xs uppercase text-muted-foreground">Positions</p>
                <ul className="flex flex-col gap-1.5 text-sm">
                  {req.positions.map((p) => (
                    <li key={p.id} className="flex items-center gap-2">
                      <StatusBadge status={p.status} />
                      {p.filled_worker_name ? <span>{p.filled_worker_name}</span> : <span className="text-muted-foreground">Unfilled</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {req.type === "VENDOR" && req.vendor_engagement_status && (
              <div className="rounded-md border border-border px-4 py-3 text-sm">
                <span className="text-muted-foreground">Vendor engagement: </span>
                <StatusBadge status={req.vendor_engagement_status} />
              </div>
            )}

            {req.vendor_messages.length > 0 && (
              <div>
                <p className="mb-2 text-xs uppercase text-muted-foreground">Messages to vendor</p>
                <ul className="flex flex-col gap-2">
                  {req.vendor_messages.map((m) => (
                    <li key={m.id} className="rounded-md border border-border px-3 py-2 text-sm">
                      <p className="font-medium">{m.subject}</p>
                      <p className="text-xs text-muted-foreground">
                        To {m.to_email} · {new Date(m.sent_at).toLocaleString()}
                      </p>
                      <p className="mt-1 whitespace-pre-line text-sm">{m.body}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="mb-3 text-xs uppercase text-muted-foreground">Timeline</p>
            <ol className="flex flex-col gap-4">
              {req.approval_events.map((e) => (
                <li key={e.id} className="border-l-2 border-border pl-3 text-sm">
                  <p className="font-medium">{e.action.replace(/_/g, " ")}</p>
                  <p className="text-xs text-muted-foreground">
                    {e.actor_name} · {new Date(e.at).toLocaleString()}
                  </p>
                  {e.note && <p className="mt-1 text-sm">{e.note}</p>}
                </li>
              ))}
              {req.approval_events.length === 0 && <p className="text-sm text-muted-foreground">No activity yet.</p>}
            </ol>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
