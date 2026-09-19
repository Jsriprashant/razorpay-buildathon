import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { formatCents } from "@/lib/money";
import type { Settings, VendorEngagement } from "@/types";

export default function Vendors() {
  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const [q, setQ] = useState("");
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());

  const { data, isLoading, isError } = useQuery<VendorEngagement[]>({
    queryKey: ["vendors", params.toString()],
    queryFn: () => api.get<VendorEngagement[]>(`/vendors?${params.toString()}`),
  });

  return (
    <div>
      <PageHeader title="Vendor engagements" description="Contractor engagements for your team, active and upcoming." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input placeholder="Search role or vendor…" className="h-9 w-56" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {isLoading && <Skeleton className="h-64 w-full" />}

      {isError && !isLoading && (
        <p className="text-sm text-destructive">Could not load vendor engagements. Please try again.</p>
      )}

      {!isLoading && !isError && (!data || data.length === 0) && (
        <EmptyState title="No vendor engagements yet" description="Approved vendor requests will appear here." />
      )}

      {!isLoading && data && data.length > 0 && (
        <Card>
          <CardContent className="overflow-x-auto pt-6">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                  <th className="pb-2 pr-4">Role</th>
                  <th className="pb-2 pr-4">Vendor</th>
                  <th className="pb-2 pr-4">Headcount</th>
                  <th className="pb-2 pr-4">Dates</th>
                  <th className="pb-2 pr-4">Lifecycle</th>
                  <th className="pb-2 pr-4">Dispatch status</th>
                  <th className="pb-2 pr-4">Contract value</th>
                </tr>
              </thead>
              <tbody>
                {data.map((v) => (
                  <tr key={v.id} className="border-b border-border/60">
                    <td className="py-2 pr-4 font-medium">{v.role_title}</td>
                    <td className="py-2 pr-4">{v.vendor_company_name}</td>
                    <td className="py-2 pr-4">{v.headcount}</td>
                    <td className="py-2 pr-4">
                      {v.start_date} → {v.end_date ?? "open"}
                    </td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={v.lifecycle ?? "UPCOMING"} />
                    </td>
                    <td className="py-2 pr-4">
                      <StatusBadge status={v.status} />
                    </td>
                    <td className="py-2 pr-4">{v.contract_value_cents ? formatCents(v.contract_value_cents, currency) : "—"}</td>
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
