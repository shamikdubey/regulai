import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Home, MessageSquare, BarChart2, FileEdit,
  Bell, Compass, FileText, ClipboardList, Settings,
  LogOut, ChevronLeft, ChevronRight,
  Menu, X, CreditCard,
  Wand2, PenLine, ShieldCheck, Shield,
  Database, FolderOpen, Search,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect, useRef } from "react";
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
  description: string;
  badge?: boolean;
  adminOnly?: boolean;
}> = [
  {
    to: "/dashboard",
    icon: Home,
    label: "Dashboard",
    group: "AI Tools",
    description: "Your compliance command center — active projects, alerts, and quick actions",
  },
  {
    to: "/query",
    icon: MessageSquare,
    label: "Ask RegulAI",
    group: "AI Tools",
    description: "Ask anything about regulations, get cited answers",
  },
  {
    to: "/gap-assessment",
    icon: BarChart2,
    label: "Gap Assessment",
    group: "AI Tools",
    description: "Identify compliance gaps across multiple jurisdictions before filing",
  },
  {
    to: "/alerts",
    icon: Bell,
    label: "Regulatory Alerts",
    group: "AI Tools",
    description: "Live alerts for high-severity regulatory changes",
    badge: true,
  },
  {
    to: "/regulatory-database",
    icon: Database,
    label: "Regulatory Database",
    group: "AI Tools",
    description: "Unified search: ingredient specs, limits, labeling, licensing",
  },
  {
    to: "/projects",
    icon: FolderOpen,
    label: "My Projects",
    group: "Filing & Documents",
    description: "Manage your active regulatory filing projects",
  },
  {
    to: "/filing-wizard",
    icon: Wand2,
    label: "Filing Wizard",
    group: "Filing & Documents",
    description: "Step-by-step guided submission workflow",
  },
  {
    to: "/document-editor",
    icon: PenLine,
    label: "Document Editor",
    group: "Filing & Documents",
    description: "Draft and edit regulatory documents",
  },
  {
    to: "/dossier",
    icon: FileEdit,
    label: "Dossier Drafting",
    group: "Filing & Documents",
    description: "Assemble technical dossiers for submission",
  },
  {
    to: "/compliance-review",
    icon: ShieldCheck,
    label: "Compliance Review",
    group: "Filing & Documents",
    description: "Review documents for compliance gaps",
  },
  {
    to: "/documents",
    icon: FileText,
    label: "My Documents",
    group: "My Library",
    description: "Your saved and uploaded regulatory documents",
  },
  {
    to: "/audit",
    icon: ClipboardList,
    label: "Audit Log",
    group: "My Library",
    description: "Full activity history and change tracking",
  },
  {
    to: "/explorer",
    icon: Compass,
    label: "Document Explorer",
    group: "My Library",
    description: "Browse the regulatory document archive",
  },
  {
    to: "/settings",
    icon: Settings,
    label: "Settings",
    group: "System",
    description: "Account and application preferences",
  },
  {
    to: "/billing",
    icon: CreditCard,
    label: "Billing",
    group: "System",
    description: "Subscription, usage, and invoices",
  },
  {
    to: "/admin",
    icon: Shield,
    label: "Admin Panel",
    group: "System",
    description: "Tenant management and user administration",
    adminOnly: true,
  },
];

// ── Page title map ────────────────────────────────────────────────────────────

const PAGE_TITLES: Record<string, string> = {
  "/dashboard":           "Dashboard",
  "/query":               "Ask RegulAI",
  "/gap-assessment":      "Gap Assessment",
  "/dossier":             "Dossier Drafting",
  "/alerts":              "Regulatory Alerts",
  "/ingredient-specs":    "Ingredient Specs",
  "/allowable-limits":    "Allowable Limits",
  "/labeling":            "Labeling Rules",
  "/licensing":           "Licensing Navigator",
  "/filing-wizard":       "Filing Wizard",
  "/document-editor":     "Document Editor",
  "/compliance-review":   "Compliance Review",
  "/explorer":            "Document Explorer",
  "/documents":           "My Documents",
  "/audit":               "Audit Log",
  "/settings":            "Settings",
  "/billing":             "Billing",
  "/admin":               "Admin Panel",
  "/regulatory-database": "Regulatory Database",
  "/projects":            "My Projects",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function AppLayout() {
  const { user, tenant, logout } = useAuthStore();
  const { sidebarOpen, setSidebarOpen } = useAppStore();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Global search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const searchWrapperRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

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

  // Cmd+K / Ctrl+K to focus search; Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchInputRef.current?.focus();
        setSearchOpen(true);
      }
      if (e.key === "Escape") {
        setSearchOpen(false);
        setSearchQuery("");
        searchInputRef.current?.blur();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Click outside to close search dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        searchWrapperRef.current &&
        !searchWrapperRef.current.contains(e.target as Node)
      ) {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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

  // Filtered search results — respects adminOnly, max 6
  const searchResults =
    searchQuery.length > 0
      ? NAV.filter(
          (item) =>
            (!item.adminOnly || user?.role === "admin") &&
            item.label.toLowerCase().includes(searchQuery.toLowerCase()),
        ).slice(0, 6)
      : [];

  // ── SidebarContent ──────────────────────────────────────────────────────────

  const SidebarContent = ({
    collapsed,
    onClose,
  }: {
    collapsed: boolean;
    onClose?: () => void;
  }) => {
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

              {onClose ? (
                <button
                  onClick={onClose}
                  className="text-[#94a3b8] hover:text-[#0f172a] transition-colors flex-shrink-0"
                  aria-label="Close menu"
                >
                  <X size={15} />
                </button>
              ) : (
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
          ).map(({ to, icon: Icon, label, group, description, badge }) => {
            const showGroup = !collapsed && group !== lastGroup;
            lastGroup = group;
            const badgeCount = badge ? highAlertCount : 0;

            return (
              <div key={to}>
                {showGroup && (
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
                      title={collapsed ? `${label} — ${description}` : undefined}
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

        {/* Top bar */}
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

          {/* Global search */}
          <div ref={searchWrapperRef} className="relative hidden sm:block">
            <div className="flex items-center gap-1.5 bg-[#f1f5f9] border border-[#e2e8f0] rounded-lg px-2.5 py-1.5 w-48 focus-within:border-[#2563eb] focus-within:bg-white transition-all">
              <Search size={12} className="text-[#94a3b8] flex-shrink-0" />
              <input
                ref={searchInputRef}
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setSearchOpen(true);
                }}
                onFocus={() => setSearchOpen(true)}
                placeholder="Search… ⌘K"
                className="flex-1 text-xs bg-transparent outline-none text-[#0f172a] placeholder-[#cbd5e1] min-w-0"
              />
            </div>

            {/* Search dropdown */}
            {searchOpen && searchResults.length > 0 && (
              <div className="absolute top-full right-0 mt-1.5 w-72 bg-white border border-[#e2e8f0] rounded-xl shadow-lg z-50 overflow-hidden">
                {searchResults.map((item) => (
                  <button
                    key={item.to}
                    onClick={() => {
                      navigate(item.to);
                      setSearchOpen(false);
                      setSearchQuery("");
                    }}
                    className="w-full flex items-center gap-2.5 px-3 py-2.5 hover:bg-[#f1f5f9] transition-colors text-left"
                  >
                    <item.icon size={14} className="text-[#2563eb] flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-[#0f172a] truncate">
                        {item.label}
                      </p>
                      <p className="text-[10px] text-[#94a3b8] truncate">
                        {item.description}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

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
