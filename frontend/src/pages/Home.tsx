import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { HomeChecklist } from "@/components/layout/HomeChecklist";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { KpiOut } from "@/types";

export default function Home() {
  const { user } = useAuth();
  const { data, isLoading } = useQuery<KpiOut>({ queryKey: ["kpis"], queryFn: () => api.get<KpiOut>("/kpis") });

  return (
    <div>
      <PageHeader title={`Welcome, ${user?.name ?? ""}`} description="Your headcount, requests and vendor status at a glance." />

      {user?.role === "MANAGER" && <HomeChecklist />}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      )}

      {!isLoading && data && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {data.cards.map((card) => {
              const content = (
                <Card className="h-full transition-colors hover:border-primary/40" title={card.formula}>
                  <CardHeader className="pb-2">
                    <CardTitle>{card.label}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-xl font-semibold text-foreground">{card.display}</p>
                    {card.secondary && <p className="mt-1 text-xs text-muted-foreground">{card.secondary}</p>}
                  </CardContent>
                </Card>
              );
              return card.click_through ? (
                <Link key={card.key} to={card.click_through}>
                  {content}
                </Link>
              ) : (
                <div key={card.key}>{content}</div>
              );
            })}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>This month at a glance</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-foreground">{data.variance_summary}</CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
