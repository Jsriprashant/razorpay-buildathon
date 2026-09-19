import { Outlet } from "react-router-dom";
import { DemoBanner } from "@/components/layout/DemoBanner";

/** Public careers pages have no sidebar/auth — anyone can browse postings. */
export default function CareersLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <DemoBanner />
      <header className="border-b border-border px-6 py-4">
        <span className="text-lg font-bold tracking-tight text-foreground">HeadcountHQ Careers</span>
      </header>
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
