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
import type { VendorCompany } from "@/types";

export default function HrVendorCompanies() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());

  const { data, isLoading, isError } = useQuery<VendorCompany[]>({
    queryKey: ["vendor-companies", params.toString()],
    queryFn: () => api.get<VendorCompany[]>(`/hr/vendor-companies?${params.toString()}`),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post<VendorCompany>("/hr/vendor-companies", { name, contact_name: contactName, contact_email: contactEmail }),
    onSuccess: () => {
      setName("");
      setContactName("");
      setContactEmail("");
      queryClient.invalidateQueries({ queryKey: ["vendor-companies"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not add this vendor company."),
  });

  return (
    <div className="space-y-6">
      <PageHeader title="Vendor companies" description="The directory of staffing vendors used for engagement requests." />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="pt-6">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Input placeholder="Search name or contact…" className="h-10 w-64 bg-background" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            {isLoading && <Skeleton className="h-48 w-full" />}
            {isError && !isLoading && (
              <p className="text-sm text-destructive">Could not load vendor companies. Please try again.</p>
            )}
            {!isLoading && !isError && (!data || data.length === 0) && <EmptyState title="No vendor companies yet" />}
            {!isLoading && data && data.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase text-muted-foreground">
                      <th className="pb-3 pr-4">Name</th>
                    <th className="pb-2 pr-4">Contact</th>
                    <th className="pb-2 pr-4">Email</th>
                  </tr>
                </thead>
                <tbody>
                   {data.map((v) => (
                     <tr key={v.id} className="border-b border-border/60 transition-colors hover:bg-accent/40">
                       <td className="py-3 pr-4 font-semibold">{v.name}</td>
                      <td className="py-2 pr-4">{v.contact_name}</td>
                      <td className="py-2 pr-4">{v.contact_email}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <h2 className="mb-4 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Add a vendor company</h2>
            <form
              className="flex flex-col gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                setError(null);
                mutation.mutate();
              }}
            >
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="v_name">Company name</Label>
                <Input id="v_name" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="v_contact">Contact name</Label>
                <Input id="v_contact" value={contactName} onChange={(e) => setContactName(e.target.value)} required />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="v_email">Contact email</Label>
                <Input id="v_email" type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} required />
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Adding…" : "Add vendor company"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
