import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Placeholder for the foundation phase — wired up to GET /notifications and
 * POST /notifications/read in the rollover/notifications task. Rendering a
 * disabled-looking bell here (rather than a fake dropdown) avoids a
 * dead-button UI in the meantime.
 */
export function NotificationBell() {
  return (
    <Button variant="ghost" size="icon" disabled title="Notifications (coming soon)">
      <Bell className="h-5 w-5" />
    </Button>
  );
}
