import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { EmptyState } from "@/components/layout/EmptyState";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { BriefcaseBusiness, MapPin, Search } from "lucide-react";
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
    <div className="mx-auto max-w-5xl">
      <div className="mb-10 max-w-2xl">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Join CONTINUUM</p>
        <h1 className="font-logotype text-4xl font-medium tracking-tight text-foreground sm:text-5xl">Work that makes room for people.</h1>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground">Bring your sharpest thinking to the operating system for thoughtful workforce planning.</p>
      </div>

      <div className="mb-8 flex max-w-xl items-center gap-2 rounded-2xl border border-border/70 bg-card p-2 shadow-card">
        <Search className="ml-2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search roles or locations…" className="h-10 border-0 bg-transparent shadow-none focus-visible:ring-0" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>

      {isLoading && <Skeleton className="h-48 w-full" />}

      {!isLoading && (!data || data.length === 0) && (
        <EmptyState title="No open roles right now" description="Check back soon — new roles are posted regularly." />
      )}

      <div className="flex flex-col gap-3">
        {data?.map((p) => (
          <Card key={p.slug} className="transition-shadow hover:shadow-card-hover">
            <CardContent className="flex flex-wrap items-center justify-between gap-5 pt-6">
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary"><BriefcaseBusiness className="h-5 w-5" /></div>
                <div>
                <Link to={`/careers/${p.slug}`} className="text-lg font-semibold text-foreground hover:text-primary hover:underline">
                  {p.title}
                </Link>
                <p className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                  <MapPin className="h-3.5 w-3.5" /> {p.location} <span>·</span> {p.openings} opening{p.openings === 1 ? "" : "s"}
                </p>
                </div>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to={`/careers/${p.slug}`}>View role</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
