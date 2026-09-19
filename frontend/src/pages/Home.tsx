import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/lib/auth";

export default function Home() {
  const { user } = useAuth();
  return (
    <div>
      <PageHeader title={`Welcome, ${user?.name ?? ""}`} description="Your headcount, requests and vendor status at a glance." />
      <Card>
        <CardHeader>
          <CardTitle>Foundation in place</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          KPI cards, recon highlights and quick actions for this page are built in the next task. Use the sidebar to
          explore the rest of the app shell.
        </CardContent>
      </Card>
    </div>
  );
}
