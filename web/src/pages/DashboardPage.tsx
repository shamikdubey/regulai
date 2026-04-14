import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessageSquare, TrendingUp, FileEdit, Bell, FileText,
  ArrowRight, AlertTriangle, Clock, CheckCircle, Zap,
  FolderOpen, Plus,
} from "lucide-react";
import { api, getApiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn, JURISDICTION_MAP, DOMAIN_MAP } from "@/lib/utils";

const QUICK_ACTIONS = [
  { icon: MessageSquare, label: "Ask a compliance question", desc: "Query the AI about any regulation", path: "/query", color: "#2563eb" },
  { icon: TrendingUp,    label: "Run gap assessment",        desc: "Multi-jurisdiction product analysis", path: "/gap-assessment", color: "#8b5cf6" },
  { icon: FileEdit,      label: "Draft submission dossier",  desc: "AI-generated regulatory dossier", path: "/dossier", color: "#0d9488" },
  { icon: Bell,          label: "View regulatory alerts",    desc: "Recent changes & updates", path: "/alerts", color: "#f59e0b" },
  { icon: FileText,      label: "Upload a document",         desc: "Add to your regulation corpus", path: "/documents", color: "#dc2626" },
];

const STAT_CONFIG = [
  { key: "queries",    label: "Total Queries",       color: "#2563eb" },
  { key: "documents",  label: "Documents Indexed",   color: "#8b5cf6" },
  { key: "bodies",     label: "Regulatory Bodies",   color: "#0d9488" },
  { key: "alerts",     label: "Active Alerts",       color: "#f59e0b" },
];

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

  const recentQueries  = auditQ.data || [];
  const recentAlerts   = (alertsQ.data || []).slice(0, 5);
  const statsData = {
    queries:   auditAllQ.data?.length ?? 0,
    documents: docsQ.data?.length ?? 0,
    bodies:    bodiesQ.data?.length ?? 0,
    alerts:    (alertsQ.data || []).filter(a => a.severity === "high").length,
  };

  const hourOfDay = new Date().getHours();
  const greeting = hourOfDay < 12 ? "Good morning" : hourOfDay < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Greeting */}
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="font-serif text-3xl text-[#0f172a] mb-1">
          {greeting}, {user?.name?.split(" ")[0] || "there"}
        </h1>
        <p className="text-sm text-[#94a3b8]">
          {tenant?.name} · {tenant?.allowedJurisdictions?.length || 10} jurisdictions ·{" "}
          {tenant?.allowedDomains?.length || 5} domains licensed
        </p>
      </motion.div>

      {/* Active Projects */}
      {((projectsQ.data ?? []).length > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-mono text-[#94a3b8] uppercase tracking-widest">
              Active Projects
            </h2>
            <button
              onClick={() => navigate("/projects")}
              className="text-[10px] font-mono text-[#2563eb] hover:text-[#1d4ed8] flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight size={10} />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(projectsQ.data ?? []).slice(0, 3).map((proj: any) => {
              const country = JURISDICTION_MAP[proj.country];
              return (
                <button
                  key={proj.id}
                  onClick={() => navigate(`/projects/${proj.id}`)}
                  className="text-left p-4 rounded-xl bg-white border border-[#e2e8f0] hover:border-[#cbd5e1] hover:bg-[#f8fafc] transition-all shadow-sm group"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <p className="text-xs font-bold text-[#0f172a] truncate leading-snug">
                      {proj.product_name}
                    </p>
                    <ArrowRight
                      size={12}
                      className="text-[#cbd5e1] group-hover:text-[#2563eb] transition-colors flex-shrink-0 mt-0.5"
                    />
                  </div>
                  {country && (
                    <p className="text-[10px] text-[#94a3b8] mb-2">
                      {country.flag} {country.label}
                    </p>
                  )}
                  <div className="h-1.5 bg-[#e2e8f0] rounded-full overflow-hidden mb-1">
                    <div
                      className="h-full bg-[#2563eb] rounded-full transition-all"
                      style={{ width: `${proj.progress}%` }}
                    />
                  </div>
                  <p className="text-[10px] font-mono text-[#94a3b8]">
                    {proj.progress}% complete
                  </p>
                </button>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* New project CTA — only when no projects exist */}
      {!projectsQ.isLoading && (projectsQ.data ?? []).length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-8"
        >
          <button
            onClick={() => navigate("/projects")}
            className="w-full flex items-center gap-4 p-4 rounded-xl bg-white border border-dashed border-[#cbd5e1] hover:border-[#2563eb] hover:bg-[#f8fafc] transition-all text-left group"
          >
            <div className="w-9 h-9 rounded-xl bg-[#eff6ff] flex items-center justify-center flex-shrink-0">
              <FolderOpen size={18} className="text-[#2563eb]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold text-[#0f172a]">Start your first filing project</p>
              <p className="text-[10px] text-[#94a3b8] mt-0.5">
                Track gap analysis, checklist, documents, and compliance review in one place
              </p>
            </div>
            <div className="flex items-center gap-1 text-xs font-bold text-[#2563eb] flex-shrink-0 group-hover:gap-2 transition-all">
              <Plus size={13} />
              New project
            </div>
          </button>
        </motion.div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {STAT_CONFIG.map((s, i) => (
          <motion.div
            key={s.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-white border border-[#e2e8f0] rounded-xl p-4 shadow-sm"
          >
            <div className="text-[10px] font-mono text-[#94a3b8] uppercase tracking-widest mb-2">{s.label}</div>
            <div className="text-2xl font-bold font-mono" style={{ color: s.color }}>
              {statsData[s.key as keyof typeof statsData]}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="mb-8">
        <h2 className="text-xs font-mono text-[#94a3b8] uppercase tracking-widest mb-3">Quick Actions</h2>
        <div className="grid grid-cols-5 gap-3">
          {QUICK_ACTIONS.map((a, i) => (
            <motion.button
              key={a.path}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              onClick={() => navigate(a.path)}
              className="text-left p-4 rounded-xl bg-white border border-[#e2e8f0] hover:border-[#cbd5e1] hover:bg-[#f8fafc] transition-all group shadow-sm"
            >
              <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                style={{ background: `${a.color}12`, border: `1px solid ${a.color}30` }}>
                <a.icon size={16} style={{ color: a.color }} />
              </div>
              <p className="text-xs font-semibold text-[#0f172a] leading-snug mb-1">{a.label}</p>
              <p className="text-[10px] text-[#94a3b8] leading-relaxed">{a.desc}</p>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Two-column: Recent activity + Alerts */}
      <div className="grid grid-cols-2 gap-6">
        {/* Recent queries */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="bg-white border border-[#e2e8f0] rounded-xl overflow-hidden shadow-sm"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2e8f0]">
            <span className="text-xs font-mono text-[#94a3b8] uppercase tracking-widest">Recent Queries</span>
            <button onClick={() => navigate("/audit")}
              className="text-[10px] font-mono text-[#2563eb] hover:text-[#1d4ed8] flex items-center gap-1 transition-colors">
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentQueries.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#94a3b8]">
              <MessageSquare size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No queries yet</p>
              <button onClick={() => navigate("/query")} className="text-[10px] text-[#2563eb] mt-2 hover:underline">
                Ask your first question →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#e2e8f0]">
              {recentQueries.map(q => {
                const j = q.jurisdiction ? JURISDICTION_MAP[q.jurisdiction] : null;
                const d = q.domain ? DOMAIN_MAP[q.domain] : null;
                const conf = q.confidence ?? 0;
                return (
                  <div key={q.id} className="px-5 py-3 hover:bg-[#f8fafc] transition-colors">
                    <p className="text-xs text-[#0f172a] truncate mb-1">{q.query}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-[#94a3b8]">
                      {j && <span>{j.flag} {j.label}</span>}
                      {d && <span style={{ color: d.color }}>{q.domain?.toUpperCase()}</span>}
                      <span style={{ color: conf >= 0.8 ? "#0d9488" : conf >= 0.6 ? "#f59e0b" : "#dc2626" }}>
                        {Math.round(conf * 100)}% conf
                      </span>
                      <span className="ml-auto">{new Date(q.created_at).toLocaleDateString()}</span>
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
          className="bg-white border border-[#e2e8f0] rounded-xl overflow-hidden shadow-sm"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2e8f0]">
            <span className="text-xs font-mono text-[#94a3b8] uppercase tracking-widest flex items-center gap-2">
              Regulatory Alerts
              {recentAlerts.filter(a => a.severity === "high").length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[rgba(220,38,38,0.1)] text-[#dc2626]">
                  {recentAlerts.filter(a => a.severity === "high").length} high
                </span>
              )}
            </span>
            <button onClick={() => navigate("/alerts")}
              className="text-[10px] font-mono text-[#f59e0b] hover:text-[#d97706] flex items-center gap-1 transition-colors">
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentAlerts.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#94a3b8]">
              <Bell size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No alerts loaded</p>
              <button onClick={() => navigate("/alerts")} className="text-[10px] text-[#f59e0b] mt-2 hover:underline">
                Go to Alerts →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#e2e8f0]">
              {recentAlerts.map(a => {
                const j = JURISDICTION_MAP[a.jurisdiction];
                const sevColor = a.severity === "high" ? "#dc2626" : a.severity === "medium" ? "#f59e0b" : "#0d9488";
                return (
                  <div key={a.id} onClick={() => navigate("/alerts")}
                    className="px-5 py-3 hover:bg-[#f8fafc] transition-colors cursor-pointer">
                    <div className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: sevColor }} />
                      <div className="min-w-0">
                        <p className="text-xs text-[#0f172a] leading-snug truncate">{a.title}</p>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-[#94a3b8]">
                          {j && <span>{j.flag} {j.label}</span>}
                          <span className="capitalize">{a.change_type.toLowerCase()}</span>
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

      {/* Coverage row */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="mt-6 bg-white border border-[#e2e8f0] rounded-xl p-5 shadow-sm"
      >
        <h3 className="text-xs font-mono text-[#94a3b8] uppercase tracking-widest mb-4">Jurisdiction Coverage</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(JURISDICTION_MAP).map(([key, j]) => (
            <button
              key={key}
              onClick={() => navigate(`/explorer`)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#f8fafc] border border-[#e2e8f0] hover:border-[#cbd5e1] transition-colors text-xs text-[#64748b]"
            >
              {j.flag} {j.label}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
