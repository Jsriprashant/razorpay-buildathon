import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  Banknote,
  BarChart3,
  Briefcase,
  Building2,
  CalendarClock,
  LineChart,
  PiggyBank,
  Users,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { HomeChecklist } from "@/components/layout/HomeChecklist";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { KpiOut } from "@/types";

// Some KPI cards embed an "A / B" ratio in their display string (e.g. "12 / 15
// FTE" or "$4,200 / $5,000"). Where that pattern exists, surface it as a
// progress bar instead of asking the reader to parse the text themselves.
const RATIO_CARD_KEYS = new Set(["headcount_vs_plan", "ytd_actual_vs_plan"]);

function extractRatio(display: string): number | null {
  const match = display.match(/[₹$€£]?([\d,]+(?:\.\d+)?)\s*\/\s*[₹$€£]?([\d,]+(?:\.\d+)?)/);
  if (!match) return null;
  const numerator = Number(match[1].replace(/,/g, ""));
  const denominator = Number(match[2].replace(/,/g, ""));
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) return null;
  return Math.min(100, Math.max(0, (numerator / denominator) * 100));
}

const CARD_ICONS: Record<string, LucideIcon> = {
  headcount_vs_plan: Users,
  cost_this_month: Wallet,
  plan_this_month: CalendarClock,
  variance: BarChart3,
  available_budget: PiggyBank,
  unspent_earlier: Banknote,
  ytd_actual_vs_plan: BarChart3,
  year_end_outlook: LineChart,
  pipeline: Briefcase,
  open_positions: Briefcase,
  vendor_expiring: Building2,
  unresolved_recon_flags: AlertTriangle,
};

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
              const Icon = CARD_ICONS[card.key] ?? BarChart3;
              const ratio = RATIO_CARD_KEYS.has(card.key) ? extractRatio(card.display) : null;
              const content = (
                <Card className="h-full shadow-card hover:shadow-card-hover" title={card.formula}>
                  <CardHeader className="flex-row items-start justify-between space-y-0 pb-2">
                    <CardTitle>{card.label}</CardTitle>
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-blue-soft text-primary">
                      <Icon className="h-4 w-4" />
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="font-numeric text-2xl font-bold text-foreground">{card.display}</p>
                    {card.secondary && <p className="mt-1 text-xs text-muted-foreground">{card.secondary}</p>}
                    {ratio !== null && <Progress value={ratio} className="mt-3" />}
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

          <Card className="shadow-card-hover">
            <CardHeader className="rounded-t-2xl bg-gradient-blue-soft">
              <CardTitle>This month at a glance</CardTitle>
            </CardHeader>
            <CardContent className="pt-6 text-sm text-foreground">{data.variance_summary}</CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
