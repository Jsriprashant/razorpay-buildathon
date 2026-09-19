import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { Settings } from "@/types";

const FIELDS: { key: keyof Settings; label: string; type: string; hint: string }[] = [
  { key: "currency", label: "Currency", type: "text", hint: "3-letter code, e.g. USD" },
  { key: "fy_start_month", label: "Fiscal year start month", type: "number", hint: "1-12" },
  { key: "vendor_hours_per_month", label: "Vendor hours / month", type: "number", hint: "Default hours used to cost a vendor headcount" },
  { key: "attrition_pct_monthly", label: "Attrition % (monthly)", type: "number", hint: "Used by the forecast" },
  { key: "fte_lead_days", label: "FTE lead time (days)", type: "number", hint: "Time to fill an FTE requisition" },
  { key: "vendor_lead_days", label: "Vendor lead time (days)", type: "number", hint: "Time to onboard a vendor" },
  { key: "demo_today", label: "Demo \"today\" override (YYYY-MM-DD)", type: "text", hint: "Leave blank to use the real date" },
];

export default function HrSettings() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const [form, setForm] = useState<Partial<Settings> | null>(null);
  const [saved, setSaved] = useState(false);

  const current = form ?? data ?? null;

  const mutation = useMutation({
    mutationFn: (payload: Partial<Settings>) => api.put<Settings>("/settings", payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(["settings"], updated);
      setForm(null);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  function handleChange(key: keyof Settings, value: string) {
    setForm({ ...(current ?? {}), [key]: value === "" ? null : value });
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!current) return;
    mutation.mutate(current);
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Anything configurable in HeadcountHQ lives here — nothing is hardcoded." />
      <Card className="max-w-2xl">
        <CardContent className="pt-6">
          {isLoading && <Skeleton className="h-64 w-full" />}
          {current && (
            <form onSubmit={handleSubmit} className="grid gap-5 sm:grid-cols-2">
              {FIELDS.map(({ key, label, type, hint }) => (
                <div key={key} className="flex flex-col gap-1.5">
                  <Label htmlFor={key}>{label}</Label>
                  <Input
                    id={key}
                    type={type}
                    value={(current[key] as string | number | null) ?? ""}
                    onChange={(e) => handleChange(key, e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">{hint}</p>
                </div>
              ))}
              <div className="flex items-center gap-3 sm:col-span-2">
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? "Saving…" : "Save settings"}
                </Button>
                {saved && <span className="text-sm text-success">Saved.</span>}
                {mutation.isError && <span className="text-sm text-destructive">Could not save settings.</span>}
              </div>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
