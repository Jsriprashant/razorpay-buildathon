import { Badge } from "@/components/ui/badge";

const VARIANTS: Record<string, "default" | "secondary" | "success" | "warning" | "destructive" | "outline"> = {
  DRAFT: "outline",
  SUBMITTED: "secondary",
  APPROVED: "success",
  REJECTED: "destructive",
  CHANGES_REQUESTED: "warning",
  CANCELLED: "outline",
  PUBLISHED: "success",
  PAUSED: "warning",
  CLOSED: "outline",
  NEW: "secondary",
  SHORTLISTED: "default",
  HIRED: "success",
  AWAITING_DISPATCH: "secondary",
  MESSAGE_SENT: "default",
  CONFIRMED: "success",
  DECLINED: "destructive",
  OPEN: "secondary",
  FILLED: "success",
  ACTIVE: "success",
  UPCOMING: "secondary",
  ENDED: "outline",
  WITHIN_PLAN: "success",
  EXCEEDS_PLAN: "warning",
  WITHIN_BUDGET: "success",
  OVER_BUDGET: "warning",
  NO_DATA: "outline",
};

const LABELS: Record<string, string> = {
  CHANGES_REQUESTED: "Changes requested",
  AWAITING_DISPATCH: "Awaiting dispatch",
  MESSAGE_SENT: "Message sent",
  WITHIN_PLAN: "Within plan",
  EXCEEDS_PLAN: "Exceeds plan",
  WITHIN_BUDGET: "Within budget",
  OVER_BUDGET: "Over budget",
  NO_DATA: "No plan data",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const variant = VARIANTS[status] ?? "outline";
  const label = LABELS[status] ?? status.charAt(0) + status.slice(1).toLowerCase().replace(/_/g, " ");
  return (
    <Badge variant={variant} className={className}>
      {label}
    </Badge>
  );
}
