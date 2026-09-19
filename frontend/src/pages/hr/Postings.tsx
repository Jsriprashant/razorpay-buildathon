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
import type { JobPosting, PostingStatus } from "@/types";

export default function HrPostings() {
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<PostingStatus | "ALL">("ALL");
  const [error, setError] = useState<string | null>(null);

  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (status !== "ALL") params.set("status", status);

  const { data, isLoading, isError } = useQuery<JobPosting[]>({
    queryKey: ["hr-postings", params.toString()],
    queryFn: () => api.get<JobPosting[]>(`/hr/postings?${params.toString()}`),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: PostingStatus }) => api.patch(`/hr/postings/${id}`, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["hr-postings"] }),
    onError: (err) => setError(err instanceof ApiError ? err.message : "Could not update this posting."),
  });

  return (
    <div>
      <PageHeader title="Job postings" description="Pause or close postings and see applicant counts." />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input placeholder="Search title or location…" className="h-9 w-56" value={q} onChange={(e) => setQ(e.target.value)} />
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={status}
          onChange={(e) => setStatus(e.target.value as PostingStatus | "ALL")}
        >
          <option value="ALL">All statuses</option>
          <option value="PUBLISHED">Published</option>
          <option value="PAUSED">Paused</option>
          <option value="CLOSED">Closed</option>
        </select>
      </div>

      {error && <p className="mb-4 text-sm text-destructive">{error}</p>}

      {isLoading && <Skeleton className="h-64 w-full" />}

      {isError && !isLoading && <p className="text-sm text-destructive">Could not load postings. Please try again.</p>}

      {!isLoading && !isError && (!data || data.length === 0) && (
        <EmptyState title="No postings yet" description="Approved FTE requests publish a posting automatically." />
      )}

      <div className="flex flex-col gap-3">
        {data?.map((p) => (
          <Card key={p.id}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
              <div>
                <Link to={`/careers/${p.slug}`} target="_blank" className="font-medium hover:underline">
                  {p.title}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {p.location} · {p.openings} openings · {p.open_position_count} still open · {p.applicant_count} applicant
                  {p.applicant_count === 1 ? "" : "s"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={p.status} />
                {p.status === "PUBLISHED" && (
                  <Button size="sm" variant="outline" onClick={() => mutation.mutate({ id: p.id, status: "PAUSED" })}>
                    Pause
                  </Button>
                )}
                {p.status === "PAUSED" && (
                  <Button size="sm" variant="outline" onClick={() => mutation.mutate({ id: p.id, status: "PUBLISHED" })}>
                    Resume
                  </Button>
                )}
                {p.status !== "CLOSED" && (
                  <Button size="sm" variant="destructive" onClick={() => mutation.mutate({ id: p.id, status: "CLOSED" })}>
                    Close
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
