import { NavLink } from "react-router-dom";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import {
  BarChart3,
  Building2,
  CalendarClock,
  ClipboardList,
  History,
  Home,
  Inbox,
  LayoutList,
  Mail,
  Settings,
  Users,
} from "lucide-react";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  hrOnly?: boolean;
}

const MAIN_NAV: NavItem[] = [
  { to: "/home", label: "Home", icon: Home },
  { to: "/roster", label: "Roster", icon: Users },
  { to: "/recon", label: "Reconciliation", icon: ClipboardList },
  { to: "/requests", label: "Requests", icon: LayoutList },
  { to: "/forecast", label: "Forecast", icon: BarChart3 },
  { to: "/plan", label: "Plan", icon: CalendarClock },
  { to: "/vendors", label: "Vendors", icon: Building2 },
  { to: "/history", label: "History", icon: History },
];

const HR_NAV: NavItem[] = [
  { to: "/hr/inbox", label: "Approval Inbox", icon: Inbox },
  { to: "/hr/postings", label: "Postings", icon: LayoutList },
  { to: "/hr/applications", label: "Applications", icon: Users },
  { to: "/hr/vendor-dispatch", label: "Vendor Dispatch", icon: Mail },
  { to: "/hr/vendors", label: "Vendor Companies", icon: Building2 },
  { to: "/hr/settings", label: "Settings", icon: Settings },
];

function NavSection({ items }: { items: NavItem[] }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-active text-sidebar-active-foreground shadow-card"
                : "text-sidebar-foreground hover:bg-white/60 hover:text-sidebar-active-foreground",
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}

export function Sidebar() {
  const { user } = useAuth();
  return (
    <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-sidebar-border bg-sidebar px-3 py-5 md:flex">
      <div className="px-3">
        <span className="font-logotype text-xl font-medium tracking-tight text-foreground">HeadcountHQ</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        <NavSection items={MAIN_NAV} />
        {user?.role === "HR" && (
          <div className="mt-6">
            <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-sidebar-foreground/60">HR</p>
            <NavSection items={HR_NAV} />
          </div>
        )}
      </div>
    </aside>
  );
}
