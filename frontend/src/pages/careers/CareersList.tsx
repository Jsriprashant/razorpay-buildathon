import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { PublicPostingListItem } from "@/types";

export default function CareersList() {
  const [q, setQ] = useState("");
  const { data, isLoading } = useQuery<PublicPostingListItem[]>({
    queryKey: ["public-postings", q],
    queryFn: () => api.get<PublicPostingListItem[]>(`/public/postings${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  });

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Open roles</h1>
      <p className="mb-6 text-sm text-muted-foreground">Browse our current openings and apply below.</p>

      <Input
        placeholder="Search roles or locations…"
        className="mb-6 h-10"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />

      {isLoading && <Skeleton className="h-48 w-full" />}

      {!isLoading && (!data || data.length === 0) && (
        <EmptyState title="No open roles right now" description="Check back soon — new roles are posted regularly." />
      )}

      <div className="flex flex-col gap-3">
        {data?.map((p) => (
          <Card key={p.slug}>
            <CardContent className="flex items-center justify-between pt-6">
              <div>
                <Link to={`/careers/${p.slug}`} className="text-lg font-medium hover:underline">
                  {p.title}
                </Link>
                <p className="text-sm text-muted-foreground">
                  {p.location} · {p.openings} opening{p.openings === 1 ? "" : "s"}
                </p>
              </div>
              <Link to={`/careers/${p.slug}`} className="text-sm font-medium text-primary hover:underline">
                View & apply →
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
