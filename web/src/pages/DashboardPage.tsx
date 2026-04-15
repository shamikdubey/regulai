import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessageSquare, TrendingUp, FileEdit, Bell, FileText,
  ArrowRight, AlertTriangle, Clock, CheckCircle, Zap,
  FolderOpen, Plus, ShieldCheck,
} from "lucide-react";
import { api, getApiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn, JURISDICTION_MAP, DOMAIN_MAP } from "@/lib/utils";

// ── Constants ─────────────────────────────────────────────────────────────────

const QUICK_ACTIONS = [
  { icon: MessageSquare, label: "Ask a compliance question", desc: "Query the AI about any regulation",   path: "/query",          color: "#047857" },
  { icon: TrendingUp,    label: "Run gap assessment",        desc: "Multi-jurisdiction product analysis", path: "/gap-assessment", color: "#8b5cf6" },
  { icon: FileEdit,      label: "Draft submission dossier",  desc: "AI-generated regulatory dossier",     path: "/dossier",        color: "#0d9488" },
  { icon: Bell,          label: "View regulatory alerts",    desc: "Recent changes & updates",            path: "/alerts",         color: "#f59e0b" },
  { icon: FileText,      label: "Upload a document",         desc: "Add to your regulation corpus",       path: "/documents",      color: "#dc2626" },
];

const STAT_CONFIG = [
  { key: "queries",   label: "Total Queries",     color: "#047857" },
  { key: "documents", label: "Documents Indexed", color: "#8b5cf6" },
  { key: "bodies",    label: "Regulatory Bodies", color: "#0d9488" },
  { key: "alerts",    label: "Active Alerts",     color: "#f59e0b" },
];

const SEV_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  critical: { color: "#dc2626", bg: "rgba(220,38,38,0.08)",  label: "Critical" },
  high:     { color: "#f59e0b", bg: "rgba(245,158,11,0.08)", label: "High"     },
  medium:   { color: "#eab308", bg: "rgba(234,179,8,0.08)",  label: "Medium"   },
  low:      { color: "#0d9488", bg: "rgba(13,148,136,0.08)", label: "Low"      },
};

const PIPELINE_STEPS = ["Gap Analysis", "Filing", "Documents", "Review"];

const DOMAIN_COLORS: Record<string, string> = {
  FOOD: "#f59e0b", food: "#f59e0b",
  MEDICAL_DEVICE: "#047857", medical_device: "#047857",
  PHARMA: "#0d9488", pharma: "#0d9488",
  NUTRA: "#8b5cf6", nutra: "#8b5cf6",
};

function getActiveStepIndex(progress: number): number {
  if (progress >= 75) return 3;
  if (progress >= 50) return 2;
  if (progress >= 25) return 1;
  return 0;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user, tenant } = useAuthStore();
  const navigate = useNavigate();

  const auditQ    = useQuery({ queryKey: ["audit", 0, null, null], queryFn: () => api.getAuditLog({ limit: 5 }) });
  const alertsQ   = useQuery({ queryKey: ["alerts", "", "", ""], queryFn: () => api.getAlerts() });
  const bodiesQ   = useQuery({ queryKey: ["bodies", null, null], queryFn: () => api.getBodies() });
  const docsQ     = useQuery({ queryKey: ["documents"], queryFn: api.getDocuments });
  const auditAllQ = useQuery({ queryKey: ["audit-all-count"], queryFn: () => api.getAuditLog({ limit: 200 }) });
  const projectsQ = useQuery({
    queryKey: ["filing-projects"],
    queryFn: () => getApiClient().get<any[]>("/filing-wizard/projects").then((r) => r.data),
  });

  const recentQueries = auditQ.data || [];
  const recentAlerts  = (alertsQ.data || []).slice(0, 5);
  const previewAlerts = (alertsQ.data || []).slice(0, 3);
  const allProjects   = projectsQ.data ?? [];
  const highAlertCount = (alertsQ.data || []).filter((a) => a.severity === "high" || a.severity === "critical").length;

  const statsData = {
    queries:   auditAllQ.data?.length ?? 0,
    documents: docsQ.data?.length ?? 0,
    bodies:    bodiesQ.data?.length ?? 0,
    alerts:    (alertsQ.data || []).filter((a) => a.severity === "high").length,
  };

  const hourOfDay = new Date().getHours();
  const greeting  = hourOfDay < 12 ? "Good morning" : hourOfDay < 18 ? "Good afternoon" : "Good evening";
  const firstName = user?.name?.split(" ")[0] || "there";

  return (
    <div className="p-6 max-w-6xl mx-auto">

      {/* ── A) Welcome banner ─────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6 rounded-2xl bg-gradient-to-r from-[#ecfdf5] via-[#f0f9ff] to-[#ecfdf5] border border-[#a7f3d0] p-6"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[#111827] mb-1">
              {greeting}, {firstName}
            </h1>
            <p className="text-sm text-[#3b82f6] font-medium mb-2">
              Here's your compliance overview for today
            </p>
            <p className="text-xs text-[#6b7280]">
              {tenant?.name}
              {tenant?.allowedJurisdictions?.length
                ? ` · ${tenant.allowedJurisdictions.length} jurisdictions`
                : " · 10 jurisdictions"}
              {tenant?.allowedDomains?.length
                ? ` · ${tenant.allowedDomains.length} domains licensed`
                : " · 5 domains licensed"}
            </p>
          </div>
          <div className="w-12 h-12 rounded-xl bg-[#d1fae5] flex items-center justify-center flex-shrink-0">
            <ShieldCheck size={24} className="text-[#047857]" />
          </div>
        </div>
      </motion.div>

      {/* ── B) Active Projects widget ──────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05 }}
        className="mb-6"
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest">
            Active Projects
          </h2>
          <button
            onClick={() => navigate("/projects")}
            className="text-[10px] font-mono text-[#047857] hover:text-[#065f46] flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight size={10} />
          </button>
        </div>

        {projectsQ.isLoading ? (
          <div className="h-32 bg-white border border-[#e2ede9] rounded-xl flex items-center justify-center">
            <span className="text-xs text-[#9ca3af]">Loading projects…</span>
          </div>
        ) : allProjects.length === 0 ? (
          <button
            onClick={() => navigate("/projects")}
            className="w-full flex items-center gap-4 p-4 rounded-xl bg-white border border-dashed border-[#cbd5e1] hover:border-[#047857] hover:bg-[#f7faf9] transition-all text-left group"
          >
            <div className="w-9 h-9 rounded-xl bg-[#ecfdf5] flex items-center justify-center flex-shrink-0">
              <FolderOpen size={18} className="text-[#047857]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-[#111827]">No active projects</p>
              <p className="text-[10px] text-[#374151] mt-0.5">
                Track gap analysis, checklist, documents, and compliance review in one place
              </p>
            </div>
            <span className="text-xs font-bold text-[#047857] flex items-center gap-1 flex-shrink-0 group-hover:gap-2 transition-all">
              Start your first project →
            </span>
          </button>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {allProjects.slice(0, 3).map((proj: any) => {
              const country      = JURISDICTION_MAP[proj.country];
              const domainColor  = DOMAIN_COLORS[proj.domain] ?? "#6b7280";
              const activeStep   = getActiveStepIndex(proj.progress);
              return (
                <button
                  key={proj.id}
                  onClick={() => navigate(`/projects/${proj.id}`)}
                  className="text-left p-4 rounded-xl bg-white border border-[#e2ede9] hover:border-[#cbd5e1] hover:bg-[#f7faf9] transition-all shadow-sm group flex flex-col gap-3"
                >
                  {/* Name + domain */}
                  <div>
                    <p className="text-xs font-bold text-[#111827] truncate leading-snug mb-1">
                      {proj.product_name}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {country && (
                        <span className="text-[10px] text-[#6b7280]">
                          {country.flag} {country.label}
                        </span>
                      )}
                      <span
                        className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
                        style={{
                          background: `${domainColor}12`,
                          color: domainColor,
                          border: `1px solid ${domainColor}25`,
                        }}
                      >
                        {proj.domain?.replace(/_/g, " ")}
                      </span>
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div>
                    <div className="h-1.5 bg-[#e2ede9] rounded-full overflow-hidden mb-1.5">
                      <div
                        className="h-full bg-[#047857] rounded-full transition-all"
                        style={{ width: `${proj.progress}%` }}
                      />
                    </div>
                    <p className="text-[10px] font-mono text-[#374151]">
                      {proj.progress}% complete
                    </p>
                  </div>

                  {/* Pipeline step dots */}
                  <div className="flex items-center gap-1.5">
                    {PIPELINE_STEPS.map((step, si) => (
                      <div
                        key={step}
                        className={cn(
                          "flex-1 h-1 rounded-full transition-all",
                          si < activeStep
                            ? "bg-[#0d9488]"
                            : si === activeStep
                              ? "bg-[#047857]"
                              : "bg-[#e2ede9]",
                        )}
                        title={step}
                      />
                    ))}
                  </div>

                  {/* Continue */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-[#374151]">
                      {PIPELINE_STEPS[activeStep]}
                    </span>
                    <span className="text-[10px] font-bold text-[#047857] flex items-center gap-1 group-hover:gap-1.5 transition-all">
                      Continue <ArrowRight size={10} />
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* ── C) Quick Actions bar ──────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="grid grid-cols-3 gap-4">

          {/* New Filing Project */}
          <button
            onClick={() => navigate("/projects?new=true")}
            className="flex items-center gap-4 p-5 rounded-2xl bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98] transition-all shadow-sm group"
          >
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
              <FolderOpen size={20} className="text-white" />
            </div>
            <div className="text-left min-w-0">
              <p className="text-sm font-bold leading-snug">New Filing Project</p>
              <p className="text-[11px] text-blue-200 mt-0.5">Start a new submission</p>
            </div>
            <Plus size={16} className="ml-auto opacity-70 flex-shrink-0" />
          </button>

          {/* Ask RegulAI */}
          <button
            onClick={() => navigate("/query")}
            className="flex items-center gap-4 p-5 rounded-2xl bg-white border border-[#e2ede9] hover:border-[#047857] hover:bg-[#f7faf9] active:scale-[0.98] transition-all shadow-sm group"
          >
            <div className="w-10 h-10 rounded-xl bg-[#ecfdf5] flex items-center justify-center flex-shrink-0">
              <MessageSquare size={20} className="text-[#047857]" />
            </div>
            <div className="text-left min-w-0">
              <p className="text-sm font-bold text-[#111827] leading-snug">Ask RegulAI</p>
              <p className="text-[11px] text-[#374151] mt-0.5">Query any regulation</p>
            </div>
            <ArrowRight
              size={16}
              className="ml-auto text-[#cbd5e1] group-hover:text-[#047857] flex-shrink-0 transition-colors"
            />
          </button>

          {/* Check Alerts */}
          <button
            onClick={() => navigate("/alerts")}
            className="flex items-center gap-4 p-5 rounded-2xl bg-white border border-[#e2ede9] hover:border-[#f59e0b] hover:bg-[#fffbeb] active:scale-[0.98] transition-all shadow-sm group"
          >
            <div className="w-10 h-10 rounded-xl bg-[#fffbeb] flex items-center justify-center flex-shrink-0 relative">
              <Bell size={20} className="text-[#f59e0b]" />
              {highAlertCount > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#dc2626] text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                  {highAlertCount > 9 ? "9+" : highAlertCount}
                </span>
              )}
            </div>
            <div className="text-left min-w-0">
              <p className="text-sm font-bold text-[#111827] leading-snug">Check Alerts</p>
              <p className="text-[11px] text-[#374151] mt-0.5">
                {highAlertCount > 0
                  ? `${highAlertCount} high-severity alert${highAlertCount !== 1 ? "s" : ""}`
                  : "No critical alerts"}
              </p>
            </div>
            <ArrowRight
              size={16}
              className="ml-auto text-[#cbd5e1] group-hover:text-[#f59e0b] flex-shrink-0 transition-colors"
            />
          </button>
        </div>
      </motion.div>

      {/* ── D) Recent Alerts preview ──────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="mb-8 bg-white border border-[#e2ede9] rounded-2xl overflow-hidden shadow-sm"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2ede9]">
          <span className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest">
            Recent Regulatory Alerts
          </span>
          <button
            onClick={() => navigate("/alerts")}
            className="text-[10px] font-mono text-[#f59e0b] hover:text-[#d97706] flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight size={10} />
          </button>
        </div>

        {alertsQ.isLoading ? (
          <div className="px-5 py-8 text-center text-xs text-[#9ca3af]">
            Loading alerts…
          </div>
        ) : previewAlerts.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-[#9ca3af]">
            <Bell size={24} className="mb-2 opacity-30" />
            <p className="text-xs font-mono">No alerts loaded</p>
            <button
              onClick={() => navigate("/alerts")}
              className="text-[10px] text-[#f59e0b] mt-2 hover:underline"
            >
              Go to Alerts →
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[#f0fdf4]">
            {previewAlerts.map((a: any) => {
              const sev = SEV_CONFIG[a.severity] ?? SEV_CONFIG.low;
              const j   = JURISDICTION_MAP[a.jurisdiction];
              return (
                <div
                  key={a.id}
                  onClick={() => navigate("/alerts")}
                  className="px-5 py-3.5 hover:bg-[#f7faf9] transition-colors cursor-pointer flex items-start gap-3"
                >
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 mt-0.5"
                    style={{ background: sev.bg, color: sev.color }}
                  >
                    {sev.label}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-[#111827] truncate">{a.title}</p>
                    <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-[#374151]">
                      {j && <span>{j.flag} {j.label}</span>}
                      {a.change_type && (
                        <span className="capitalize">{a.change_type.toLowerCase()}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-[#374151] flex-shrink-0 mt-0.5">
                    {a.published_at
                      ? new Date(a.published_at).toLocaleDateString()
                      : a.effective_date ?? ""}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      {/* ── E) Stats row (existing — kept) ────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {STAT_CONFIG.map((s, i) => (
          <motion.div
            key={s.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-white border border-[#e2ede9] rounded-xl p-4 shadow-sm"
          >
            <div className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-widest mb-2">
              {s.label}
            </div>
            <div className="text-2xl font-bold font-mono" style={{ color: s.color }}>
              {statsData[s.key as keyof typeof statsData]}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quick actions (existing — kept) */}
      <div className="mb-8">
        <h2 className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest mb-3">
          Quick Actions
        </h2>
        <div className="grid grid-cols-5 gap-3">
          {QUICK_ACTIONS.map((a, i) => (
            <motion.button
              key={a.path}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              onClick={() => navigate(a.path)}
              className="text-left p-4 rounded-xl bg-white border border-[#e2ede9] hover:border-[#cbd5e1] hover:bg-[#f7faf9] transition-all group shadow-sm"
            >
              <div
                className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                style={{
                  background: `${a.color}12`,
                  border: `1px solid ${a.color}30`,
                }}
              >
                <a.icon size={16} style={{ color: a.color }} />
              </div>
              <p className="text-xs font-semibold text-[#111827] leading-snug mb-1">
                {a.label}
              </p>
              <p className="text-[10px] text-[#374151] leading-relaxed">{a.desc}</p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Two-column: Recent activity + Alerts (existing — kept) */}
      <div className="grid grid-cols-2 gap-6">
        {/* Recent queries */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white border border-[#e2ede9] rounded-xl overflow-hidden shadow-sm"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2ede9]">
            <span className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest">
              Recent Queries
            </span>
            <button
              onClick={() => navigate("/audit")}
              className="text-[10px] font-mono text-[#047857] hover:text-[#065f46] flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentQueries.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#9ca3af]">
              <MessageSquare size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No queries yet</p>
              <button
                onClick={() => navigate("/query")}
                className="text-[10px] text-[#047857] mt-2 hover:underline"
              >
                Ask your first question →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#e2ede9]">
              {recentQueries.map((q) => {
                const j    = q.jurisdiction ? JURISDICTION_MAP[q.jurisdiction] : null;
                const d    = q.domain ? DOMAIN_MAP[q.domain] : null;
                const conf = q.confidence ?? 0;
                return (
                  <div
                    key={q.id}
                    className="px-5 py-3 hover:bg-[#f7faf9] transition-colors"
                  >
                    <p className="text-xs text-[#111827] truncate mb-1">{q.query}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-[#374151]">
                      {j && <span>{j.flag} {j.label}</span>}
                      {d && <span style={{ color: d.color }}>{q.domain?.toUpperCase()}</span>}
                      <span
                        style={{
                          color:
                            conf >= 0.8
                              ? "#0d9488"
                              : conf >= 0.6
                                ? "#f59e0b"
                                : "#dc2626",
                        }}
                      >
                        {Math.round(conf * 100)}% conf
                      </span>
                      <span className="ml-auto">
                        {new Date(q.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </motion.div>

        {/* Recent alerts */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="bg-white border border-[#e2ede9] rounded-xl overflow-hidden shadow-sm"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2ede9]">
            <span className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest flex items-center gap-2">
              Regulatory Alerts
              {recentAlerts.filter((a) => a.severity === "high").length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[rgba(220,38,38,0.1)] text-[#dc2626]">
                  {recentAlerts.filter((a) => a.severity === "high").length} high
                </span>
              )}
            </span>
            <button
              onClick={() => navigate("/alerts")}
              className="text-[10px] font-mono text-[#f59e0b] hover:text-[#d97706] flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentAlerts.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#9ca3af]">
              <Bell size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No alerts loaded</p>
              <button
                onClick={() => navigate("/alerts")}
                className="text-[10px] text-[#f59e0b] mt-2 hover:underline"
              >
                Go to Alerts →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#e2ede9]">
              {recentAlerts.map((a) => {
                const j = JURISDICTION_MAP[a.jurisdiction];
                const sevColor =
                  a.severity === "high"
                    ? "#dc2626"
                    : a.severity === "medium"
                      ? "#f59e0b"
                      : "#0d9488";
                return (
                  <div
                    key={a.id}
                    onClick={() => navigate("/alerts")}
                    className="px-5 py-3 hover:bg-[#f7faf9] transition-colors cursor-pointer"
                  >
                    <div className="flex items-start gap-2">
                      <span
                        className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5"
                        style={{ background: sevColor }}
                      />
                      <div className="min-w-0">
                        <p className="text-xs text-[#111827] leading-snug truncate">
                          {a.title}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-[#374151]">
                          {j && <span>{j.flag} {j.label}</span>}
                          <span className="capitalize">
                            {a.change_type.toLowerCase()}
                          </span>
                          {a.effective_date && <span>{a.effective_date}</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </motion.div>
      </div>

      {/* Coverage row (existing — kept) */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-6 bg-white border border-[#e2ede9] rounded-xl p-5 shadow-sm"
      >
        <h3 className="text-xs font-mono text-[#9ca3af] uppercase tracking-widest mb-4">
          Jurisdiction Coverage
        </h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(JURISDICTION_MAP).map(([key, j]) => (
            <button
              key={key}
              onClick={() => navigate("/explorer")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f7faf9] border border-[#e2ede9] hover:border-[#cbd5e1] transition-colors text-xs text-[#6b7280]"
            >
              {j.flag} {j.label}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
