import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import type { HiringRequest, RequestStatus, RequestType, Settings } from "@/types";

const STATUS_OPTIONS: (RequestStatus | "ALL")[] = [
  "ALL",
  "DRAFT",
  "SUBMITTED",
  "APPROVED",
  "CHANGES_REQUESTED",
  "REJECTED",
  "CANCELLED",
];
const TYPE_OPTIONS: (RequestType | "ALL")[] = ["ALL", "FTE", "VENDOR"];

function duplicateParams(r: HiringRequest): URLSearchParams {
  const p = new URLSearchParams();
  p.set("type", r.type);
  p.set("role_title", r.role_title);
  if (r.grade) p.set("grade", r.grade);
  p.set("quantity", String(r.quantity));
  p.set("target_start_date", r.target_start_date);
  if (r.annual_salary_cents) p.set("annual_salary_cents", String(r.annual_salary_cents));
  if (r.vendor_company_id) p.set("vendor_company_id", String(r.vendor_company_id));
  if (r.hourly_rate_cents) p.set("hourly_rate_cents", String(r.hourly_rate_cents));
  if (r.hours_per_month) p.set("hours_per_month", String(r.hours_per_month));
  if (r.end_date) p.set("end_date", r.end_date);
  return p;
}

export default function Requests() {
  const [status, setStatus] = useState<RequestStatus | "ALL">("ALL");
  const [type, setType] = useState<RequestType | "ALL">("ALL");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("-created_at");

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const params = useMemo(() => {
    const p = new URLSearchParams();
    if (status !== "ALL") p.set("status", status);
    if (type !== "ALL") p.set("type", type);
    if (q.trim()) p.set("q", q.trim());
    if (sort) p.set("sort", sort);
    return p.toString();
  }, [status, type, q, sort]);

  const { data, isLoading } = useQuery<HiringRequest[]>({
    queryKey: ["requests", params],
    queryFn: () => api.get<HiringRequest[]>(`/requests?${params}`),
  });

  return (
    <div>
      <PageHeader
        title="Hiring requests"
        description="Requests you've raised for new headcount, FTE or vendor."
        actions={
          <Button asChild>
            <Link to="/requests/new">New request</Link>
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search role or justification…"
          className="h-9 w-56"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={status}
          onChange={(e) => setStatus(e.target.value as RequestStatus | "ALL")}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All statuses" : s.replace(/_/g, " ")}
            </option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={type}
          onChange={(e) => setType(e.target.value as RequestType | "ALL")}
        >
          {TYPE_OPTIONS.map((t) => (
            <option key={t} value={t}>
              {t === "ALL" ? "All types" : t}
            </option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="-created_at">Newest first</option>
          <option value="created_at">Oldest first</option>
          <option value="target_start_date">Start date</option>
          <option value="role_title">Role title</option>
          <option value="status">Status</option>
        </select>
      </div>

      {isLoading && <Skeleton className="h-64 w-full" />}

      {!isLoading && (!data || data.length === 0) && (
        <EmptyState
          title="No requests match these filters"
          description="Try widening your filters, or raise a new hiring request."
          action={
            <Button asChild variant="outline">
              <Link to="/requests/new">New request</Link>
            </Button>
          }
        />
      )}

      {!isLoading && data && data.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Qty</th>
                  <th className="pb-2 pr-4">Target start</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Value</th>
                  <th className="pb-2 pr-4"></th>
                </tr>
              </thead>
              <tbody>
                {data.map((r) => (
                  <tr key={r.id} className="border-b border-border/60 hover:bg-accent/40">
                    <td className="py-2 pr-4">
                      <Link to={`/requests/${r.id}`} className="font-medium text-foreground hover:underline">
                        {r.role_title}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">{r.type}</td>
                    <td className="py-2 pr-4">{r.quantity}</td>
                    <td className="py-2 pr-4">{r.target_start_date}</td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-2 pr-4">
                      {r.type === "FTE"
                        ? r.annual_salary_cents
                          ? `${formatCents(r.annual_salary_cents, currency)}/yr`
                          : "—"
                        : r.contract_value_cents
                          ? `${formatCents(r.contract_value_cents, currency)} total`
                          : "—"}
                    </td>
                    <td className="py-2 pr-4">
                      <Link
                        to={`/requests/new?${duplicateParams(r).toString()}`}
                        className="text-xs font-medium text-primary hover:underline"
                      >
                        Duplicate
                      </Link>
                    </td>
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
