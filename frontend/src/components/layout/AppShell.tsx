import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { RolloverGate } from "@/components/layout/RolloverGate";
import { AssistantCopilot } from "@/components/layout/AssistantCopilot";

export function AppShell() {
  return (
    <div className="flex h-screen flex-col">
      <DemoBanner />
      <RolloverGate />
      <AssistantCopilot />
      <div className="flex min-h-0 flex-1">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <main className="flex-1 overflow-y-auto bg-background p-6 lg:p-8">
            <div className="mx-auto w-full max-w-7xl">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
