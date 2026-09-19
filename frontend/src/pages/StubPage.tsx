import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/layout/EmptyState";

export function StubPage({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <PageHeader title={title} />
      <EmptyState title="Coming soon" description={description} />
    </div>
  );
}
