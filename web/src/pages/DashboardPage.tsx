import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  MessageSquare, TrendingUp, FileEdit, Bell, FileText,
  ArrowRight, AlertTriangle, Clock, CheckCircle, Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn, JURISDICTION_MAP, DOMAIN_MAP } from "@/lib/utils";

const QUICK_ACTIONS = [
  { icon: MessageSquare, label: "Ask a compliance question", desc: "Query the AI about any regulation", path: "/query", color: "#00d4aa" },
  { icon: TrendingUp,    label: "Run gap assessment",        desc: "Multi-jurisdiction product analysis", path: "/gap-assessment", color: "#6699ff" },
  { icon: FileEdit,      label: "Draft submission dossier",  desc: "AI-generated regulatory dossier", path: "/dossier", color: "#a78bfa" },
  { icon: Bell,          label: "View regulatory alerts",    desc: "Recent changes & updates", path: "/alerts", color: "#f5a623" },
  { icon: FileText,      label: "Upload a document",         desc: "Add to your regulation corpus", path: "/documents", color: "#ff6b35" },
];

const STAT_CONFIG = [
  { key: "queries",    label: "Total Queries",       color: "#00d4aa" },
  { key: "documents",  label: "Documents Indexed",   color: "#6699ff" },
  { key: "bodies",     label: "Regulatory Bodies",   color: "#a78bfa" },
  { key: "alerts",     label: "Active Alerts",       color: "#f5a623" },
];

export default function DashboardPage() {
  const { user, tenant } = useAuthStore();
  const navigate = useNavigate();

  const auditQ    = useQuery({ queryKey: ["audit", 0, null, null], queryFn: () => api.getAuditLog({ limit: 5 }) });
  const alertsQ   = useQuery({ queryKey: ["alerts", "", "", ""], queryFn: () => api.getAlerts() });
  const bodiesQ   = useQuery({ queryKey: ["bodies", null, null], queryFn: () => api.getBodies() });
  const docsQ     = useQuery({ queryKey: ["documents"], queryFn: api.getDocuments });
  const auditAllQ = useQuery({ queryKey: ["audit-all-count"], queryFn: () => api.getAuditLog({ limit: 200 }) });

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
        <h1 className="font-serif text-3xl text-[#e8ecf2] mb-1">
          {greeting}, {user?.name?.split(" ")[0] || "there"}
        </h1>
        <p className="text-sm text-[#4a5568]">
          {tenant?.name} · {tenant?.allowed_jurisdictions?.length || 10} jurisdictions ·{" "}
          {tenant?.allowed_domains?.length || 5} domains licensed
        </p>
      </motion.div>

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {STAT_CONFIG.map((s, i) => (
          <motion.div
            key={s.key}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-[#111318] border border-[#1f2530] rounded-xl p-4"
          >
            <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">{s.label}</div>
            <div className="text-2xl font-bold font-mono" style={{ color: s.color }}>
              {statsData[s.key as keyof typeof statsData]}
            </div>
          </motion.div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="mb-8">
        <h2 className="text-xs font-mono text-[#4a5568] uppercase tracking-widest mb-3">Quick Actions</h2>
        <div className="grid grid-cols-5 gap-3">
          {QUICK_ACTIONS.map((a, i) => (
            <motion.button
              key={a.path}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              onClick={() => navigate(a.path)}
              className="text-left p-4 rounded-xl bg-[#111318] border border-[#1f2530] hover:border-[#2a3040] hover:bg-[#181c24] transition-all group"
            >
              <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-3"
                style={{ background: `${a.color}18`, border: `1px solid ${a.color}40` }}>
                <a.icon size={16} style={{ color: a.color }} />
              </div>
              <p className="text-xs font-semibold text-[#e8ecf2] leading-snug mb-1">{a.label}</p>
              <p className="text-[10px] text-[#4a5568] leading-relaxed">{a.desc}</p>
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
          className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2530]">
            <span className="text-xs font-mono text-[#4a5568] uppercase tracking-widest">Recent Queries</span>
            <button onClick={() => navigate("/audit")}
              className="text-[10px] font-mono text-[#00d4aa] hover:text-white flex items-center gap-1 transition-colors">
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentQueries.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#4a5568]">
              <MessageSquare size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No queries yet</p>
              <button onClick={() => navigate("/query")} className="text-[10px] text-[#00d4aa] mt-2 hover:underline">
                Ask your first question →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#1f2530]">
              {recentQueries.map(q => {
                const j = q.jurisdiction ? JURISDICTION_MAP[q.jurisdiction] : null;
                const d = q.domain ? DOMAIN_MAP[q.domain] : null;
                const conf = q.confidence ?? 0;
                return (
                  <div key={q.id} className="px-5 py-3 hover:bg-[#181c24] transition-colors">
                    <p className="text-xs text-[#e8ecf2] truncate mb-1">{q.query}</p>
                    <div className="flex items-center gap-3 text-[10px] font-mono text-[#4a5568]">
                      {j && <span>{j.flag} {j.label}</span>}
                      {d && <span style={{ color: d.color }}>{q.domain?.toUpperCase()}</span>}
                      <span style={{ color: conf >= 0.8 ? "#00d4aa" : conf >= 0.6 ? "#f5a623" : "#ff4757" }}>
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
          className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2530]">
            <span className="text-xs font-mono text-[#4a5568] uppercase tracking-widest flex items-center gap-2">
              Regulatory Alerts
              {recentAlerts.filter(a => a.severity === "high").length > 0 && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-[rgba(255,71,87,0.15)] text-[#ff4757]">
                  {recentAlerts.filter(a => a.severity === "high").length} high
                </span>
              )}
            </span>
            <button onClick={() => navigate("/alerts")}
              className="text-[10px] font-mono text-[#f5a623] hover:text-white flex items-center gap-1 transition-colors">
              View all <ArrowRight size={10} />
            </button>
          </div>

          {recentAlerts.length === 0 ? (
            <div className="flex flex-col items-center py-10 text-[#4a5568]">
              <Bell size={24} className="mb-2 opacity-30" />
              <p className="text-xs font-mono">No alerts loaded</p>
              <button onClick={() => navigate("/alerts")} className="text-[10px] text-[#f5a623] mt-2 hover:underline">
                Go to Alerts →
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#1f2530]">
              {recentAlerts.map(a => {
                const j = JURISDICTION_MAP[a.jurisdiction];
                const sevColor = a.severity === "high" ? "#ff4757" : a.severity === "medium" ? "#f5a623" : "#00d4aa";
                return (
                  <div key={a.id} onClick={() => navigate("/alerts")}
                    className="px-5 py-3 hover:bg-[#181c24] transition-colors cursor-pointer">
                    <div className="flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5" style={{ background: sevColor }} />
                      <div className="min-w-0">
                        <p className="text-xs text-[#e8ecf2] leading-snug truncate">{a.title}</p>
                        <div className="flex items-center gap-2 mt-0.5 text-[10px] font-mono text-[#4a5568]">
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
        className="mt-6 bg-[#111318] border border-[#1f2530] rounded-xl p-5"
      >
        <h3 className="text-xs font-mono text-[#4a5568] uppercase tracking-widest mb-4">Jurisdiction Coverage</h3>
        <div className="flex flex-wrap gap-2">
          {Object.entries(JURISDICTION_MAP).map(([key, j]) => (
            <button
              key={key}
              onClick={() => navigate(`/explorer`)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181c24] border border-[#2a3040] hover:border-[#4a5568] transition-colors text-xs text-[#8892a4]"
            >
              {j.flag} {j.label}
            </button>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
