import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { formatCents } from "@/lib/money";
import { parseDateOnlyUTC } from "@/lib/dates";
import type { RequestDetail, RequestType, Settings, VendorCompany } from "@/types";

const GRADES = ["G1", "G2", "G3", "G4"];

export default function RequestNew() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const editId = params.get("edit");

  const { data: settings } = useQuery<Settings>({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings") });
  const currency = settings?.currency ?? "USD";
  const { data: vendorCompanies } = useQuery<VendorCompany[]>({
    queryKey: ["vendor-companies"],
    queryFn: () => api.get<VendorCompany[]>("/hr/vendor-companies"),
  });
  const { data: existing, isLoading: isLoadingExisting } = useQuery<RequestDetail>({
    queryKey: ["requests", editId],
    queryFn: () => api.get<RequestDetail>(`/requests/${editId}`),
    enabled: !!editId,
  });

  const isForecastSuggestion = params.get("source") === "FORECAST_SUGGESTION";

  const [type, setType] = useState<RequestType>((params.get("type") as RequestType) || "FTE");
  const [roleTitle, setRoleTitle] = useState(params.get("role_title") || "");
  const [grade, setGrade] = useState(params.get("grade") || "G2");
  const [quantity, setQuantity] = useState(params.get("quantity") || "1");
  const [annualSalary, setAnnualSalary] = useState(
    params.get("annual_salary_cents") ? (Number(params.get("annual_salary_cents")) / 100).toFixed(2) : ""
  );
  const [vendorCompanyId, setVendorCompanyId] = useState(params.get("vendor_company_id") || "");
  const [hourlyRate, setHourlyRate] = useState(
    params.get("hourly_rate_cents") ? (Number(params.get("hourly_rate_cents")) / 100).toFixed(2) : ""
  );
  const [hoursPerMonth, setHoursPerMonth] = useState(
    params.get("hours_per_month") || String(settings?.vendor_hours_per_month ?? 160)
  );
  const [targetStartDate, setTargetStartDate] = useState(params.get("target_start_date") || "");
  const [endDate, setEndDate] = useState(params.get("end_date") || "");
  const [justification, setJustification] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [prefilledFromExisting, setPrefilledFromExisting] = useState(false);

  useEffect(() => {
    if (settings?.vendor_hours_per_month && !params.get("hours_per_month")) {
      setHoursPerMonth(String(settings.vendor_hours_per_month));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings]);

  useEffect(() => {
    if (!existing || prefilledFromExisting) return;
    setType(existing.type);
    setRoleTitle(existing.role_title);
    setGrade(existing.grade || "G2");
    setQuantity(String(existing.quantity));
    setAnnualSalary(existing.annual_salary_cents ? (existing.annual_salary_cents / 100).toFixed(2) : "");
    setVendorCompanyId(existing.vendor_company_id ? String(existing.vendor_company_id) : "");
    setHourlyRate(existing.hourly_rate_cents ? (existing.hourly_rate_cents / 100).toFixed(2) : "");
    setHoursPerMonth(existing.hours_per_month ? String(existing.hours_per_month) : hoursPerMonth);
    setTargetStartDate(existing.target_start_date);
    setEndDate(existing.end_date || "");
    setJustification(existing.justification);
    setPrefilledFromExisting(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [existing]);

  const contractValueCents = useMemo(() => {
    if (type !== "VENDOR") return null;
    const qty = Number(quantity) || 0;
    const rate = Math.round((Number(hourlyRate) || 0) * 100);
    const hours = Number(hoursPerMonth) || 0;
    if (!qty || !rate || !hours || !targetStartDate || !endDate) return null;
    // UTC-anchored throughout (Date.UTC / getUTC*) — never mix with local
    // getters here, since targetStartDate/endDate are date-only strings and
    // `new Date("YYYY-MM-DD")` is UTC midnight (see lib/dates.ts).
    const start = parseDateOnlyUTC(targetStartDate);
    const end = parseDateOnlyUTC(endDate);
    if (end < start) return null;
    let total = 0;
    let cursor = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth(), 1));
    const lastMonth = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), 1));
    while (cursor <= lastMonth) {
      const monthDays = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 0)).getUTCDate();
      const monthStart = cursor;
      const monthEnd = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 0));
      const activeStart = start > monthStart ? start : monthStart;
      const activeEnd = end < monthEnd ? end : monthEnd;
      const activeDays = Math.max(0, Math.round((activeEnd.getTime() - activeStart.getTime()) / 86400000) + 1);
      const fullMonthCost = qty * rate * hours;
      total += Math.round((fullMonthCost * activeDays) / monthDays);
      cursor = new Date(Date.UTC(cursor.getUTCFullYear(), cursor.getUTCMonth() + 1, 1));
    }
    return total;
  }, [type, quantity, hourlyRate, hoursPerMonth, targetStartDate, endDate]);

  const mutation = useMutation({
    mutationFn: async (submit: boolean) => {
      const payload = {
        type,
        role_title: roleTitle,
        grade: type === "FTE" ? grade : null,
        quantity: Number(quantity) || 1,
        annual_salary_cents: type === "FTE" ? Math.round((Number(annualSalary) || 0) * 100) : null,
        vendor_company_id: type === "VENDOR" ? Number(vendorCompanyId) : null,
        hourly_rate_cents: type === "VENDOR" ? Math.round((Number(hourlyRate) || 0) * 100) : null,
        hours_per_month: type === "VENDOR" ? Number(hoursPerMonth) || null : null,
        target_start_date: targetStartDate,
        end_date: type === "VENDOR" ? endDate : null,
        justification,
        source: isForecastSuggestion ? "FORECAST_SUGGESTION" : "MANUAL",
      };
      if (editId) {
        const updated = await api.patch<RequestDetail>(`/requests/${editId}`, payload);
        if (submit) {
          const action = existing?.status === "CHANGES_REQUESTED" ? "resubmit" : "submit";
          return api.post<RequestDetail>(`/requests/${editId}/${action}`);
        }
        return updated;
      }
      const created = await api.post<RequestDetail>("/requests", payload);
      return submit ? api.post<RequestDetail>(`/requests/${created.id}/submit`) : created;
    },
    onSuccess: (result) => navigate(`/requests/${result.id}`),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not save the request."),
  });

  function handleSubmit(e: React.FormEvent, submit: boolean) {
    e.preventDefault();
    setError(null);
    mutation.mutate(submit);
  }

  if (editId && isLoadingExisting) {
    return (
      <div>
        <PageHeader title="Edit request" />
        <Skeleton className="h-96 w-full max-w-2xl" />
      </div>
    );
  }

  const submitLabel = editId && existing?.status === "CHANGES_REQUESTED" ? "Resubmit" : "Submit for approval";

  return (
    <div>
      <PageHeader
        title={editId ? "Edit hiring request" : "New hiring request"}
        description="Raise an FTE requisition or a vendor engagement request."
      />

      <Card className="max-w-2xl">
        <CardContent className="pt-6">
          <form className="flex flex-col gap-5" onSubmit={(e) => handleSubmit(e, false)}>
            <div className="flex flex-col gap-1.5">
              <Label>Request type</Label>
              <Tabs value={type} onValueChange={(v) => !editId && setType(v as RequestType)}>
                <TabsList>
                  <TabsTrigger value="FTE" disabled={!!editId}>
                    FTE
                  </TabsTrigger>
                  <TabsTrigger value="VENDOR" disabled={!!editId}>
                    Vendor
                  </TabsTrigger>
                </TabsList>
              </Tabs>
              {editId && (
                <p className="text-xs text-muted-foreground">Request type can't be changed after creation.</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="role_title">Role title</Label>
              <Input id="role_title" value={roleTitle} onChange={(e) => setRoleTitle(e.target.value)} required />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  min="1"
                  max="100"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  {type === "FTE" ? "Number of openings on the resulting job posting." : "Headcount on the engagement."}
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="target_start_date">Target start date</Label>
                <Input
                  id="target_start_date"
                  type="date"
                  value={targetStartDate}
                  onChange={(e) => setTargetStartDate(e.target.value)}
                  required
                />
              </div>
            </div>

            {type === "FTE" ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="grade">Grade</Label>
                  <select
                    id="grade"
                    className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                    value={grade}
                    onChange={(e) => setGrade(e.target.value)}
                  >
                    {GRADES.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="annual_salary">Annual salary ({currency})</Label>
                  <Input
                    id="annual_salary"
                    type="number"
                    min="0"
                    step="0.01"
                    value={annualSalary}
                    onChange={(e) => setAnnualSalary(e.target.value)}
                    required
                  />
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="vendor_company">Vendor company</Label>
                  <select
                    id="vendor_company"
                    className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                    value={vendorCompanyId}
                    onChange={(e) => setVendorCompanyId(e.target.value)}
                    required
                  >
                    <option value="" disabled>
                      Select a vendor…
                    </option>
                    {vendorCompanies?.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="hourly_rate">Hourly rate ({currency})</Label>
                    <Input
                      id="hourly_rate"
                      type="number"
                      min="0"
                      step="0.01"
                      value={hourlyRate}
                      onChange={(e) => setHourlyRate(e.target.value)}
                      required
                    />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <Label htmlFor="hours_per_month">Hours / month</Label>
                    <Input
                      id="hours_per_month"
                      type="number"
                      min="1"
                      max="744"
                      value={hoursPerMonth}
                      onChange={(e) => setHoursPerMonth(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="end_date">End date</Label>
                  <Input id="end_date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required />
                </div>
                <div className="rounded-md border border-border bg-muted/40 px-4 py-3 text-sm">
                  <span className="text-muted-foreground">Total contract value: </span>
                  <span className="font-semibold text-foreground">
                    {contractValueCents !== null ? formatCents(contractValueCents, currency) : "—"}
                  </span>
                </div>
              </>
            )}

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="justification">Justification</Label>
              <textarea
                id="justification"
                className="min-h-24 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex items-center gap-3">
              <Button type="submit" variant="outline" disabled={mutation.isPending}>
                Save as draft
              </Button>
              <Button type="button" onClick={(e) => handleSubmit(e, true)} disabled={mutation.isPending}>
                {mutation.isPending ? "Submitting…" : submitLabel}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
