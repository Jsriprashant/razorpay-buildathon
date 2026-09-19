import * as React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import {
  BarChart3,
  Building2,
  CalendarClock,
  ChevronsLeft,
  ChevronsRight,
  ClipboardList,
  History,
  Home,
  Inbox,
  LayoutList,
  LogOut,
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

const COLLAPSE_STORAGE_KEY = "hq_sidebar_collapsed";

function NavSection({ items, collapsed }: { items: NavItem[]; collapsed: boolean }) {
  return (
    <nav className="flex flex-col gap-0.5">
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          title={collapsed ? label : undefined}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
              collapsed && "justify-center px-0",
              isActive
                ? "bg-sidebar-active text-sidebar-active-foreground shadow-card"
                : "text-sidebar-foreground hover:bg-white/60 hover:text-sidebar-active-foreground",
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" />
          {!collapsed && label}
        </NavLink>
      ))}
    </nav>
  );
}

export function Sidebar() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [collapsed, setCollapsed] = React.useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1";
  });

  React.useEffect(() => {
    window.localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  async function handleLogout() {
    await api.post("/auth/logout");
    queryClient.clear();
    refresh();
    navigate("/login");
  }

  const initials = user?.name
    ? user.name
        .split(" ")
        .map((part) => part[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "";

  return (
    <aside
      className={cn(
        "hidden shrink-0 flex-col gap-6 border-r border-sidebar-border bg-sidebar py-4 shadow-sidebar transition-[width] duration-200 ease-in-out md:flex",
        collapsed ? "w-[76px] px-2" : "w-64 px-3",
      )}
    >
      <div className="scrollbar-hide flex-1 overflow-y-auto">
        <NavSection items={MAIN_NAV} collapsed={collapsed} />
        {user?.role === "HR" && (
          <div className="mt-6">
            {!collapsed && (
              <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wide text-sidebar-foreground/60">HR</p>
            )}
            {collapsed && <div className="my-2 h-px bg-sidebar-border" />}
            <NavSection items={HR_NAV} collapsed={collapsed} />
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={() => setCollapsed((v) => !v)}
        title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        className={cn(
          "flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-sidebar-foreground/70 transition-colors hover:bg-white/60 hover:text-sidebar-active-foreground",
          collapsed && "justify-center px-0",
        )}
      >
        {collapsed ? <ChevronsRight className="h-4 w-4 shrink-0" /> : <ChevronsLeft className="h-4 w-4 shrink-0" />}
        {!collapsed && "Collapse"}
      </button>

      {user && (
        <div className="border-t border-sidebar-border pt-4">
          <div
            className={cn(
              "flex items-center gap-2.5 rounded-xl px-1.5 py-1.5",
              collapsed && "flex-col gap-2 px-0",
            )}
            title={collapsed ? user.name : undefined}
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-blue text-xs font-semibold text-white shadow-card">
              {initials}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1 text-left">
                <p className="truncate text-sm font-medium leading-none text-foreground">{user.name}</p>
                <p className="mt-1 truncate text-xs capitalize text-sidebar-foreground/60">
                  {user.role.replace("_", " ").toLowerCase()}
                </p>
              </div>
            )}
            <button
              type="button"
              onClick={handleLogout}
              title="Log out"
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sidebar-foreground/60 transition-colors hover:bg-white/60 hover:text-destructive",
              )}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
