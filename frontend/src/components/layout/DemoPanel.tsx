import { Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Placeholder for the foundation phase — wired up to POST /demo/advance-month
 * and POST /demo/reset in the rollover/notifications task.
 */
export function DemoPanel() {
  return (
    <Button variant="outline" size="sm" disabled title="Demo controls (coming soon)" className="gap-2">
      <Settings2 className="h-4 w-4" />
      Demo panel
    </Button>
  );
}
