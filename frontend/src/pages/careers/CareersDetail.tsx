import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/layout/EmptyState";
import { api, ApiError } from "@/lib/api";
import type { PublicPostingDetail } from "@/types";

interface ApplyForm {
  name: string;
  email: string;
  phone: string;
  profile_url: string;
  note: string;
  website: string; // honeypot
}

const EMPTY_FORM: ApplyForm = { name: "", email: "", phone: "", profile_url: "", note: "", website: "" };

export default function CareersDetail() {
  const { slug } = useParams();
  const [form, setForm] = useState<ApplyForm>(EMPTY_FORM);
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const { data: posting, isLoading, isError } = useQuery<PublicPostingDetail>({
    queryKey: ["public-posting", slug],
    queryFn: () => api.get<PublicPostingDetail>(`/public/postings/${slug}`),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api.post(`/public/postings/${slug}/apply`, {
        name: form.name,
        email: form.email,
        phone: form.phone || null,
        profile_url: form.profile_url || null,
        note: form.note || null,
        website: form.website,
      }),
    onSuccess: () => setSubmitted(true),
    onError: (err) =>
      setError(err instanceof ApiError && err.status === 409 ? err.message : "Could not submit your application. Please try again."),
  });

  if (isLoading) return <Skeleton className="h-96 w-full max-w-2xl" />;
  if (isError || !posting) {
    return (
      <EmptyState
        title="This role is no longer available"
        description="It may have been filled or closed."
        action={
          <Link to="/careers" className="text-sm font-medium text-primary hover:underline">
            ← Back to open roles
          </Link>
        }
      />
    );
  }

  if (submitted) {
    return (
    <div className="mx-auto max-w-xl rounded-2xl border border-border/70 bg-card p-10 text-center shadow-card">
        <h1 className="mb-2 font-logotype text-3xl font-medium">Thanks for applying.</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          We've received your application for <span className="font-medium text-foreground">{posting.title}</span> and
          will be in touch if there's a match.
        </p>
        <Link to="/careers" className="text-sm font-medium text-primary hover:underline">
          ← Browse more roles
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_360px]">
      <div>
      <Link to="/careers" className="mb-5 inline-block text-sm text-muted-foreground hover:text-primary hover:underline">
        ← Back to open roles
      </Link>
      <h1 className="font-logotype mb-2 text-4xl font-medium tracking-tight">{posting.title}</h1>
      <p className="mb-8 text-sm text-muted-foreground">
        {posting.location} · {posting.openings} opening{posting.openings === 1 ? "" : "s"}
      </p>
      <div className="rounded-2xl border border-border/70 bg-card p-6 shadow-card">
        <p className="whitespace-pre-line text-sm leading-7 text-foreground/85">{posting.description}</p>
      </div>
      </div>

      <Card className="h-fit shadow-card-hover">
        <CardContent className="pt-6">
           <h2 className="mb-1 font-logotype text-2xl font-medium">Make your move.</h2>
           <p className="mb-5 text-sm text-muted-foreground">Tell us a little about yourself.</p>
          <form
            className="flex flex-col gap-4"
            onSubmit={(e) => {
              e.preventDefault();
              setError(null);
              mutation.mutate();
            }}
          >
            {/* Honeypot field — hidden from real users via CSS, bots often fill every input. */}
            <div className="hidden" aria-hidden="true">
              <Label htmlFor="website">Website</Label>
              <Input
                id="website"
                name="website"
                tabIndex={-1}
                autoComplete="off"
                value={form.website}
                onChange={(e) => setForm({ ...form, website: e.target.value })}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="name">Full name</Label>
              <Input id="name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="phone">Phone (optional)</Label>
              <Input id="phone" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="profile_url">LinkedIn / portfolio URL (optional)</Label>
              <Input
                id="profile_url"
                value={form.profile_url}
                onChange={(e) => setForm({ ...form, profile_url: e.target.value })}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="note">Note (optional)</Label>
               <textarea
                id="note"
                 className="min-h-24 rounded-xl border border-input bg-background px-3 py-2 text-sm outline-none transition focus:ring-2 focus:ring-ring"
                value={form.note}
                onChange={(e) => setForm({ ...form, note: e.target.value })}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Submitting…" : "Submit application"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
