import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard, MessageSquare, TrendingUp, FileEdit,
  Bell, Compass, FileText, ClipboardList, Settings,
  LogOut, ChevronLeft, ChevronRight, FlaskConical,
  BarChart2, Tag, FileCheck, Menu, X, CreditCard,
  Wand2, PenLine, ShieldCheck, Shield,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { useAuthStore } from "@/stores/authStore";
import { useAppStore } from "@/stores/appStore";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import JurisdictionSelector from "@/components/features/JurisdictionSelector";
import DomainSelector from "@/components/features/DomainSelector";

// ── Nav definition ────────────────────────────────────────────────────────────

const NAV: Array<{
  to: string;
  icon: any;
  label: string;
  group: string;
  badge?: boolean;
  adminOnly?: boolean;
}> = [
  { to: "/dashboard",         icon: LayoutDashboard, label: "Dashboard",           group: "Intelligence" },
  { to: "/query",             icon: MessageSquare,   label: "AI Query",            group: "Intelligence" },
  { to: "/gap-assessment",    icon: TrendingUp,      label: "Gap Assessment",      group: "Intelligence" },
  { to: "/dossier",           icon: FileEdit,        label: "Dossier Drafting",    group: "Intelligence" },
  { to: "/alerts",            icon: Bell,            label: "Alerts",              group: "Intelligence", badge: true },
  { to: "/ingredient-specs",  icon: FlaskConical,    label: "Ingredient Specs",    group: "Standards" },
  { to: "/allowable-limits",  icon: BarChart2,       label: "Allowable Limits",    group: "Standards" },
  { to: "/labeling",          icon: Tag,             label: "Labeling Rules",      group: "Standards" },
  { to: "/licensing",         icon: FileCheck,       label: "Licensing Navigator", group: "Standards" },
  { to: "/filing-wizard",     icon: Wand2,           label: "Filing Wizard",       group: "Workflows" },
  { to: "/document-editor",   icon: PenLine,         label: "Document Editor",     group: "Workflows" },
  { to: "/compliance-review", icon: ShieldCheck,     label: "Compliance Review",   group: "Workflows" },
  { to: "/explorer",          icon: Compass,         label: "Reg Explorer",        group: "Reference" },
  { to: "/documents",         icon: FileText,        label: "Documents",           group: "Reference" },
  { to: "/audit",             icon: ClipboardList,   label: "Audit Log",           group: "Reference" },
  { to: "/settings",          icon: Settings,        label: "Settings",            group: "System" },
  { to: "/billing",           icon: CreditCard,      label: "Billing",             group: "System" },
  { to: "/admin",             icon: Shield,          label: "Admin Panel",         group: "System", adminOnly: true },
];

// ── Page title map (for top-bar breadcrumb) ───────────────────────────────────

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":         "Dashboard",
  "/query":             "AI Query",
  "/gap-assessment":    "Gap Assessment",
  "/dossier":           "Dossier Drafting",
  "/alerts":            "Alerts",
  "/ingredient-specs":  "Ingredient Specs",
  "/allowable-limits":  "Allowable Limits",
  "/labeling":          "Labeling Rules",
  "/licensing":         "Licensing Navigator",
  "/filing-wizard":     "Filing Wizard",
  "/document-editor":   "Document Editor",
  "/compliance-review": "Compliance Review",
  "/explorer":          "Reg Explorer",
  "/documents":         "Documents",
  "/audit":             "Audit Log",
  "/settings":          "Settings",
  "/billing":           "Billing",
  "/admin":             "Admin Panel",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function AppLayout() {
  const { user, tenant, logout } = useAuthStore();
  const { sidebarOpen, setSidebarOpen } = useAppStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Collapse sidebar on small screens
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) setSidebarOpen(false);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [setSidebarOpen]);

  // Close mobile overlay on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const alertsQ = useQuery({
    queryKey: ["alerts-badge"],
    queryFn: () => api.getAlerts({ severity: "high" }),
    staleTime: 5 * 60 * 1000,
  });
  const highAlertCount = alertsQ.data?.length ?? 0;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const currentPageTitle = PAGE_TITLES[location.pathname] ?? "RegulAI";

  // ── SidebarContent ──────────────────────────────────────────────────────────
  // lastGroup declared INSIDE the component function so it resets on every render.

  const SidebarContent = ({
    collapsed,
    onClose,
  }: {
    collapsed: boolean;
    onClose?: () => void;
  }) => {
    // Reset on every render — was previously a module-level let which caused
    // stale group labels after re-renders.
    let lastGroup = "";

    return (
      <>
        {/* Logo row */}
        <div
          className={cn(
            "flex items-center gap-3 border-b border-[#e2e8f0] flex-shrink-0",
            collapsed ? "px-3 py-3.5 justify-center" : "px-4 py-3.5",
          )}
        >
          <div className="w-8 h-8 flex-shrink-0 bg-[#2563eb] rounded-lg flex items-center justify-center font-mono text-xs font-bold text-white select-none">
            R∧
          </div>

          {!collapsed && (
            <>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-bold text-[#0f172a]">RegulAI</div>
                <div className="text-[9px] text-[#94a3b8] font-mono tracking-widest">
                  COMPLIANCE AI
                </div>
              </div>

              {/* Mobile close button — shown only when onClose is provided */}
              {onClose ? (
                <button
                  onClick={onClose}
                  className="text-[#94a3b8] hover:text-[#0f172a] transition-colors flex-shrink-0"
                  aria-label="Close menu"
                >
                  <X size={15} />
                </button>
              ) : (
                /* Desktop collapse toggle */
                <button
                  onClick={() => setSidebarOpen(!sidebarOpen)}
                  className="hidden lg:flex flex-shrink-0 text-[#94a3b8] hover:text-[#0f172a] transition-colors"
                  aria-label="Toggle sidebar"
                >
                  <ChevronLeft size={15} />
                </button>
              )}
            </>
          )}

          {/* Collapsed desktop — only show expand toggle */}
          {collapsed && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="hidden lg:flex flex-shrink-0 text-[#94a3b8] hover:text-[#0f172a] transition-colors"
              aria-label="Expand sidebar"
            >
              <ChevronRight size={15} />
            </button>
          )}
        </div>

        {/* Global filters — expanded only */}
        {!collapsed && (
          <div className="px-3 py-2.5 border-b border-[#e2e8f0] space-y-2 flex-shrink-0">
            <JurisdictionSelector compact />
            <DomainSelector compact />
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV.filter(
            ({ adminOnly }) => !adminOnly || user?.role === "admin",
          ).map(({ to, icon: Icon, label, group, badge }) => {
            const showGroup = !collapsed && group !== lastGroup;
            lastGroup = group;
            const badgeCount = badge ? highAlertCount : 0;

            return (
              <div key={to}>
                {showGroup && (
                  /* Group header with blue accent bar */
                  <div className="flex items-center gap-2 px-3 pt-3 pb-1">
                    <div className="w-0.5 h-3 rounded-full bg-[#2563eb] opacity-40 flex-shrink-0" />
                    <span className="text-[9px] font-mono text-[#cbd5e1] uppercase tracking-widest">
                      {group}
                    </span>
                  </div>
                )}
                <NavLink to={to}>
                  {({ isActive }) => (
                    <div
                      className={cn(
                        "flex items-center gap-2.5 mx-2 px-2 py-2 rounded-lg transition-all cursor-pointer relative",
                        collapsed && "justify-center",
                        isActive
                          ? "bg-[#eff6ff] text-[#2563eb] border border-[#bfdbfe]"
                          : "text-[#64748b] hover:text-[#0f172a] hover:bg-[#f1f5f9]",
                      )}
                      title={collapsed ? label : undefined}
                    >
                      <Icon size={16} className="flex-shrink-0" />
                      {!collapsed && (
                        <span className="text-xs font-semibold truncate flex-1">
                          {label}
                        </span>
                      )}
                      {badgeCount > 0 && (
                        <span
                          className={cn(
                            "font-mono font-bold bg-[rgba(220,38,38,0.12)] text-[#dc2626] rounded-full flex-shrink-0 flex items-center justify-center",
                            collapsed
                              ? "text-[8px] w-4 h-4 absolute -top-1 -right-1"
                              : "text-[9px] px-1.5 py-0.5",
                          )}
                        >
                          {badgeCount}
                        </span>
                      )}
                    </div>
                  )}
                </NavLink>
              </div>
            );
          })}
        </nav>

        {/* User footer */}
        <div
          className={cn(
            "border-t border-[#e2e8f0] p-2 flex items-center gap-2 flex-shrink-0 group",
            collapsed && "justify-center",
          )}
        >
          <div className="w-7 h-7 flex-shrink-0 rounded-full bg-[#eff6ff] flex items-center justify-center text-xs font-bold text-[#2563eb]">
            {user?.name?.[0]?.toUpperCase() ||
              user?.email?.[0]?.toUpperCase() ||
              "U"}
          </div>

          {!collapsed ? (
            <>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold truncate text-[#0f172a]">
                  {user?.name || user?.email}
                </div>
                <div className="text-[10px] text-[#94a3b8] truncate">
                  {tenant?.name}
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="text-[#94a3b8] hover:text-[#dc2626] transition-colors flex-shrink-0"
                title="Sign out"
              >
                <LogOut size={14} />
              </button>
            </>
          ) : (
            /* Collapsed logout */
            <button
              onClick={handleLogout}
              className="text-[#94a3b8] hover:text-[#dc2626] transition-colors"
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          )}
        </div>
      </>
    );
  };

  // ── Layout render ───────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen bg-[#f8fafc] text-[#0f172a] overflow-hidden">

      {/* ── Mobile overlay ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/20 z-40 lg:hidden"
              onClick={() => setMobileOpen(false)}
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 28, stiffness: 300 }}
              className="fixed left-0 top-0 h-full w-72 bg-white border-r border-[#e2e8f0] z-50 lg:hidden flex flex-col shadow-xl"
            >
              <SidebarContent
                collapsed={false}
                onClose={() => setMobileOpen(false)}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ── Desktop sidebar ───────────────────────────────────────────────── */}
      <motion.aside
        animate={{ width: sidebarOpen ? 240 : 56 }}
        transition={{ duration: 0.18, ease: "easeInOut" }}
        className="hidden lg:flex flex-shrink-0 flex-col bg-white border-r border-[#e2e8f0] overflow-hidden shadow-sm"
      >
        <SidebarContent collapsed={!sidebarOpen} />
      </motion.aside>

      {/* ── Main content ──────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-hidden flex flex-col min-w-0">

        {/* Top bar with breadcrumb */}
        <header className="h-12 border-b border-[#e2e8f0] flex items-center px-4 gap-3 flex-shrink-0 bg-white shadow-sm">
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(true)}
            className="lg:hidden text-[#94a3b8] hover:text-[#0f172a] transition-colors"
            aria-label="Open menu"
          >
            <Menu size={18} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="text-[10px] text-[#cbd5e1] font-mono hidden sm:block select-none">
              RegulAI
            </span>
            <span className="text-[10px] text-[#cbd5e1] hidden sm:block select-none">
              /
            </span>
            <span className="text-xs font-semibold text-[#64748b] truncate">
              {currentPageTitle}
            </span>
          </div>

          <div className="flex-1" />

          {/* Version badge */}
          <span className="text-[10px] text-[#cbd5e1] font-mono hidden sm:block">
            v{import.meta.env.VITE_APP_VERSION || "4.0.0"}
          </span>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
