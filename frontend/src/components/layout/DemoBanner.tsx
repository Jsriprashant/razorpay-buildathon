export function DemoBanner() {
  return (
    <div className="w-full bg-warning/90 px-4 py-1.5 text-center text-xs font-medium text-warning-foreground">
      Demo mode — logins are simulated and email is not really sent. Real SSO and email delivery replace these in
      production.
    </div>
  );
}
