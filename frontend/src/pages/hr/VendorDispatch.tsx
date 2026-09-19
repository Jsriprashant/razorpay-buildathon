import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { api, ApiError } from "@/lib/api";
import { formatCents } from "@/lib/money";
import type { Settings, VendorEngagement } from "@/types";

export default function HrVendorDispatch() {
  const queryClient = useQueryClient();
  const [openId, setOpenId] = useState<number | null>(null);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";

  const [q, setQ] = useState("");
  const dispatchParams = new URLSearchParams();
  if (q.trim()) dispatchParams.set("q", q.trim());

  const { data, isLoading, isError } = useQuery<VendorEngagement[]>({
    queryKey: ["vendor-dispatch", dispatchParams.toString()],
    queryFn: () => api.get<VendorEngagement[]>(`/hr/vendor-dispatch?${dispatchParams.toString()}`),
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["vendor-dispatch"] });

  const { data: defaultMsg } = useQuery<{ subject: string; body: string }>({
    queryKey: ["default-message", openId],
    queryFn: () => api.get<{ subject: string; body: string }>(`/hr/engagements/${openId}/default-message`),
    enabled: openId !== null,
  });

  useEffect(() => {
    if (defaultMsg) {
      setSubject(defaultMsg.subject);
      setBody(defaultMsg.body);
    }
  }, [defaultMsg]);

  const sendMutation = useMutation({
    mutationFn: () => api.post(`/hr/engagements/${openId}/send`, { subject, body }),
    onSuccess: () => {
      setOpenId(null);
      invalidate();
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not send the message."),
  });

  const confirmMutation = useMutation({
    mutationFn: (id: number) => api.post(`/hr/engagements/${id}/confirm`),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not confirm this engagement."),
  });
  const declineMutation = useMutation({
    mutationFn: (id: number) => api.post(`/hr/engagements/${id}/decline`, { note: "Declined by vendor" }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not decline this engagement."),
  });

  const active = data?.find((e) => e.id === openId) ?? null;

  return (
    <div>
      <PageHeader title="Vendor dispatch" description="Send engagement details to vendors and track their response." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input placeholder="Search role or vendor…" className="h-9 w-56" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {error && !active && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {isLoading && <Skeleton className="h-64 w-full" />}

      {isError && !isLoading && (
        <p className="text-sm text-destructive">Could not load the dispatch queue. Please try again.</p>
      )}

      {!isLoading && !isError && (!data || data.length === 0) && (
        <EmptyState title="Nothing to dispatch" description="Approved vendor requests will show up here." />
      )}

      <div className="flex flex-col gap-3">
        {data?.map((e) => (
          <Card key={e.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
              <div>
                <p className="font-medium">{e.role_title}</p>
                <p className="text-sm text-muted-foreground">
                  {e.vendor_company_name} · {e.headcount} contractor{e.headcount === 1 ? "" : "s"} · {e.start_date} →{" "}
                  {e.end_date ?? "open"}
                  {e.contract_value_cents ? ` · ${formatCents(e.contract_value_cents, currency)} total` : ""}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={e.status} />
                {e.status === "AWAITING_DISPATCH" && (
                  <Button size="sm" onClick={() => { setOpenId(e.id); setError(null); }}>
                    Compose & send
                  </Button>
                )}
                {e.status === "MESSAGE_SENT" && (
                  <>
                    <Button size="sm" variant="outline" onClick={() => confirmMutation.mutate(e.id)}>
                      Mark confirmed
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => declineMutation.mutate(e.id)}>
                      Mark declined
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {active && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="w-full max-w-lg">
            <CardContent className="flex flex-col gap-4 pt-6">
              <h2 className="text-lg font-medium">Send to {active.vendor_company_name}</h2>
              <p className="text-xs text-muted-foreground">To: {active.vendor_contact_email}</p>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="subject">Subject</Label>
                <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="body">Message</Label>
                <textarea
                  id="body"
                  className="min-h-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  variant="outline"
                  type="button"
                  onClick={() => {
                    navigator.clipboard?.writeText(body);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  }}
                >
                  {copied ? "Copied!" : "Copy message"}
                </Button>
                <Button variant="outline" asChild>
                  <a
                    href={`mailto:${active.vendor_contact_email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`}
                  >
                    Open in email client
                  </a>
                </Button>
                <Button variant="ghost" onClick={() => setOpenId(null)}>
                  Cancel
                </Button>
                <Button onClick={() => sendMutation.mutate()} disabled={sendMutation.isPending}>
                  {sendMutation.isPending ? "Sending…" : "Send (simulated)"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
