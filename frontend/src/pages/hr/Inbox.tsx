import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import type { HiringRequest, RequestType } from "@/types";

export default function HrInbox() {
  const queryClient = useQueryClient();
  const [type, setType] = useState<RequestType | "ALL">("ALL");
  const [q, setQ] = useState("");
  const [selected, setSelected] = useState<number[]>([]);
  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  const params = new URLSearchParams();
  if (type !== "ALL") params.set("type", type);
  if (q.trim()) params.set("q", q.trim());

  const { data, isLoading } = useQuery<HiringRequest[]>({
    queryKey: ["hr-inbox", params.toString()],
    queryFn: () => api.get<HiringRequest[]>(`/hr/inbox?${params.toString()}`),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["hr-inbox"] });
    queryClient.invalidateQueries({ queryKey: ["requests"] });
  };

  const decisionMutation = useMutation({
    mutationFn: ({ id, action, note }: { id: number; action: "approve" | "reject" | "request-changes"; note?: string }) =>
      api.post(`/hr/requests/${id}/${action}`, { note: note || null }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Action failed."),
  });

  const bulkMutation = useMutation({
    mutationFn: () => api.post("/hr/requests/bulk-approve", { request_ids: selected }),
    onSuccess: () => {
      setSelected([]);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Bulk approve failed."),
  });

  function toggleSelected(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <div>
      <PageHeader
        title="Approval inbox"
        description="Requests awaiting your decision. Plan/budget badges are informational — you may always approve."
        actions={
          selected.length > 0 && (
            <Button onClick={() => bulkMutation.mutate()} disabled={bulkMutation.isPending}>
              {bulkMutation.isPending ? "Approving…" : `Approve ${selected.length} selected`}
            </Button>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input placeholder="Search…" className="h-9 w-56" value={q} onChange={(e) => setQ(e.target.value)} />
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={type}
          onChange={(e) => setType(e.target.value as RequestType | "ALL")}
        >
          <option value="ALL">All types</option>
          <option value="FTE">FTE</option>
          <option value="VENDOR">Vendor</option>
        </select>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {isLoading && <Skeleton className="h-64 w-full" />}

      {!isLoading && (!data || data.length === 0) && (
        <EmptyState title="Inbox zero" description="No requests are currently awaiting your review." />
      )}

      <div className="flex flex-col gap-3">
        {data?.map((r) => (
          <Card key={r.id}>
            <CardContent className="flex flex-col gap-3 pt-6">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1.5 h-4 w-4"
                    checked={selected.includes(r.id)}
                    onChange={() => toggleSelected(r.id)}
                  />
                  <div>
                    <Link to={`/requests/${r.id}`} className="font-medium hover:underline">
                      {r.role_title}
                    </Link>
                    <p className="text-sm text-muted-foreground">
                      {r.type} · {r.team_name} · qty {r.quantity} · start {r.target_start_date} · by {r.created_by_name}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {r.plan_fit && r.plan_fit !== "NO_DATA" && <StatusBadge status={r.plan_fit} />}
                  {r.budget_fit && r.budget_fit !== "NO_DATA" && <StatusBadge status={r.budget_fit} />}
                </div>
              </div>

              {r.justification && <p className="text-sm text-muted-foreground">{r.justification}</p>}

              <div className="flex flex-wrap items-center gap-2">
                <Input
                  placeholder="Note (required to reject / request changes)"
                  className="h-8 flex-1 min-w-48"
                  value={noteDrafts[r.id] || ""}
                  onChange={(e) => setNoteDrafts({ ...noteDrafts, [r.id]: e.target.value })}
                />
                <Button size="sm" onClick={() => decisionMutation.mutate({ id: r.id, action: "approve", note: noteDrafts[r.id] })}>
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => decisionMutation.mutate({ id: r.id, action: "request-changes", note: noteDrafts[r.id] })}
                >
                  Request changes
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => decisionMutation.mutate({ id: r.id, action: "reject", note: noteDrafts[r.id] })}
                >
                  Reject
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
