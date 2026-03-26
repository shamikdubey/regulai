import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Bell, BellOff, ExternalLink, Loader2, RefreshCw, Filter } from "lucide-react";
import toast from "react-hot-toast";
import { api, Alert } from "@/lib/api";
import { cn, JURISDICTION_MAP, DOMAIN_MAP, JURISDICTIONS, DOMAINS } from "@/lib/utils";

const CHANGE_TYPE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  NEW:         { label: "New",       color: "#00d4aa", bg: "rgba(0,212,170,0.1)" },
  AMENDED:     { label: "Amended",   color: "#f5a623", bg: "rgba(245,166,35,0.1)" },
  UPCOMING:    { label: "Upcoming",  color: "#6699ff", bg: "rgba(102,153,255,0.1)" },
  ENFORCEMENT: { label: "Enforcement", color: "#ff4757", bg: "rgba(255,71,87,0.1)" },
};

const SEVERITY_CONFIG: Record<string, { color: string }> = {
  high:   { color: "#ff4757" },
  medium: { color: "#f5a623" },
  low:    { color: "#00d4aa" },
};

export default function AlertsPage() {
  const qc = useQueryClient();
  const [filterJur, setFilterJur] = useState("");
  const [filterDomain, setFilterDomain] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [selected, setSelected] = useState<Alert | null>(null);
  const [showSubscribe, setShowSubscribe] = useState(false);

  const alertsQ = useQuery({
    queryKey: ["alerts", filterJur, filterDomain, filterSeverity],
    queryFn: () => api.getAlerts({
      jurisdiction: filterJur || undefined,
      domain: filterDomain || undefined,
      severity: filterSeverity || undefined,
    }),
  });

  const subQ = useQuery({
    queryKey: ["alert-subscription"],
    queryFn: api.getAlertSubscription,
  });

  const seedMut = useMutation({
    mutationFn: api.seedAlerts,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alerts"] }); toast.success("Alerts seeded"); },
  });

  const subMut = useMutation({
    mutationFn: api.subscribeAlerts,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alert-subscription"] }); toast.success("Subscription saved"); setShowSubscribe(false); },
  });

  const alerts = alertsQ.data || [];
  const highCount = alerts.filter(a => a.severity === "high").length;

  return (
    <div className="flex h-full">
      {/* Alerts list */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1f2530] flex items-center gap-4 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-serif text-xl text-[#e8ecf2]">Regulatory Alerts</h1>
              {highCount > 0 && (
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-[rgba(255,71,87,0.15)] text-[#ff4757] border border-[rgba(255,71,87,0.3)]">
                  {highCount} HIGH
                </span>
              )}
            </div>
            <p className="text-xs text-[#4a5568] mt-0.5">Recent and upcoming regulatory changes across all jurisdictions</p>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {/* Filters */}
            <select value={filterJur} onChange={e => setFilterJur(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              <option value="">All jurisdictions</option>
              {JURISDICTIONS.map(j => <option key={j.value} value={j.value}>{j.flag} {j.label}</option>)}
            </select>
            <select value={filterDomain} onChange={e => setFilterDomain(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              <option value="">All domains</option>
              {DOMAINS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
            <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              <option value="">All severity</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <button onClick={() => setShowSubscribe(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-[#111318] border border-[#2a3040] text-[#8892a4] hover:text-[#00d4aa] hover:border-[#00d4aa] transition-colors">
              <Bell size={12} /> Subscribe
            </button>

            {alerts.length === 0 && !alertsQ.isLoading && (
              <button onClick={() => seedMut.mutate()}
                disabled={seedMut.isPending}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono bg-[#111318] border border-[#2a3040] text-[#4a5568] hover:text-[#e8ecf2] transition-colors">
                {seedMut.isPending ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
                Load sample alerts
              </button>
            )}
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {alertsQ.isLoading ? (
            <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-[#4a5568]" /></div>
          ) : alerts.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-[#4a5568]">
              <Bell size={32} className="mb-3 opacity-30" />
              <p className="text-sm font-mono">No alerts found</p>
              <button onClick={() => seedMut.mutate()} className="mt-3 text-xs text-[#00d4aa] hover:underline">
                Load sample alerts
              </button>
            </div>
          ) : (
            <div className="divide-y divide-[#1f2530]">
              {alerts.map(alert => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  isSelected={selected?.id === alert.id}
                  onClick={() => setSelected(selected?.id === alert.id ? null : alert)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <motion.div
          initial={{ width: 0 }} animate={{ width: 420 }} exit={{ width: 0 }}
          className="border-l border-[#1f2530] flex-shrink-0 overflow-y-auto"
        >
          <AlertDetail alert={selected} onClose={() => setSelected(null)} />
        </motion.div>
      )}

      {/* Subscribe modal */}
      {showSubscribe && (
        <SubscribeModal
          current={subQ.data}
          onSave={data => subMut.mutate(data)}
          onClose={() => setShowSubscribe(false)}
          saving={subMut.isPending}
        />
      )}
    </div>
  );
}

function AlertRow({ alert, isSelected, onClick }: { alert: Alert; isSelected: boolean; onClick: () => void }) {
  const ct = CHANGE_TYPE_CONFIG[alert.change_type] || CHANGE_TYPE_CONFIG.NEW;
  const sev = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.medium;
  const j = JURISDICTION_MAP[alert.jurisdiction];
  const d = DOMAIN_MAP[alert.domain];

  return (
    <div
      onClick={onClick}
      className={cn(
        "px-6 py-4 cursor-pointer transition-colors hover:bg-[#111318]",
        isSelected && "bg-[rgba(0,212,170,0.04)]"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="w-2 h-2 rounded-full flex-shrink-0 mt-1.5" style={{ background: sev.color }} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start gap-2 flex-wrap mb-1.5">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded"
              style={{ color: ct.color, background: ct.bg, border: `1px solid ${ct.color}40` }}>
              {ct.label}
            </span>
            {j && <span className="text-xs text-[#4a5568] font-mono">{j.flag} {j.label}</span>}
            {d && <span className="text-xs font-mono" style={{ color: d.color }}>{alert.domain.toUpperCase()}</span>}
          </div>
          <p className="text-sm font-semibold text-[#e8ecf2] leading-snug mb-1">{alert.title}</p>
          <p className="text-xs text-[#8892a4] leading-relaxed line-clamp-2">{alert.summary}</p>
          <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-[#4a5568]">
            {alert.regulatory_body && <span>{alert.regulatory_body}</span>}
            {alert.effective_date && <span>Effective: {alert.effective_date}</span>}
            <span>{new Date(alert.published_at).toLocaleDateString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AlertDetail({ alert, onClose }: { alert: Alert; onClose: () => void }) {
  const ct = CHANGE_TYPE_CONFIG[alert.change_type] || CHANGE_TYPE_CONFIG.NEW;
  const j = JURISDICTION_MAP[alert.jurisdiction];
  const d = DOMAIN_MAP[alert.domain];

  return (
    <div className="p-5 w-[420px]">
      <div className="flex items-center justify-between mb-5">
        <span className="text-xs font-mono text-[#4a5568] uppercase tracking-widest">Alert Detail</span>
        <button onClick={onClose} className="text-xs text-[#4a5568] hover:text-[#e8ecf2] transition-colors">✕</button>
      </div>

      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-xs font-mono px-2 py-0.5 rounded"
          style={{ color: ct.color, background: ct.bg, border: `1px solid ${ct.color}40` }}>
          {ct.label}
        </span>
        <span className="text-xs font-mono text-[#4a5568]">{j?.flag} {j?.label}</span>
        {d && <span className="text-xs font-mono" style={{ color: d.color }}>{alert.domain.toUpperCase()}</span>}
      </div>

      <h2 className="text-base font-semibold text-[#e8ecf2] leading-snug mb-4">{alert.title}</h2>

      <div className="space-y-4">
        <Section label="Summary">
          <p className="text-sm text-[#8892a4] leading-relaxed">{alert.summary}</p>
        </Section>

        {alert.action_required && (
          <Section label="Action Required">
            <div className="p-3 rounded-lg bg-[rgba(0,212,170,0.05)] border border-[rgba(0,212,170,0.2)]">
              <p className="text-xs text-[#e8ecf2] leading-relaxed">{alert.action_required}</p>
            </div>
          </Section>
        )}

        <div className="grid grid-cols-2 gap-3">
          {alert.regulatory_body && <MetaBox label="Regulatory Body" value={alert.regulatory_body} />}
          {alert.effective_date && <MetaBox label="Effective Date" value={alert.effective_date} />}
          <MetaBox label="Severity" value={alert.severity.toUpperCase()}
            color={SEVERITY_CONFIG[alert.severity]?.color} />
          <MetaBox label="Published" value={new Date(alert.published_at).toLocaleDateString()} />
        </div>

        {alert.tags && alert.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {alert.tags.map(t => (
              <span key={t} className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#181c24] border border-[#2a3040] text-[#4a5568]">
                {t}
              </span>
            ))}
          </div>
        )}

        {alert.source_url && (
          <a href={alert.source_url} target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs text-[#6699ff] hover:underline">
            <ExternalLink size={11} /> View official source
          </a>
        )}
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-1.5">{label}</p>
      {children}
    </div>
  );
}

function MetaBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="px-3 py-2.5 rounded-lg bg-[#181c24] border border-[#2a3040]">
      <p className="text-[9px] font-mono text-[#4a5568] uppercase tracking-widest mb-1">{label}</p>
      <p className="text-xs font-mono font-semibold" style={{ color: color || "#e8ecf2" }}>{value}</p>
    </div>
  );
}

function SubscribeModal({ current, onSave, onClose, saving }: {
  current: any; onSave: (d: any) => void; onClose: () => void; saving: boolean;
}) {
  const [jurs, setJurs] = useState<string[]>(current?.jurisdictions || []);
  const [doms, setDoms] = useState<string[]>(current?.domains || []);
  const [thresh, setThresh] = useState(current?.severity_threshold || "medium");

  const toggle = (arr: string[], item: string, set: (v: string[]) => void) => {
    set(arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item]);
  };

  return (
    <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
      <div className="bg-[#111318] border border-[#2a3040] rounded-2xl p-6 w-[480px] max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-[#e8ecf2]">Alert Subscriptions</h3>
          <button onClick={onClose} className="text-[#4a5568] hover:text-[#e8ecf2]">✕</button>
        </div>

        <div className="space-y-5">
          <div>
            <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">Jurisdictions (empty = all)</p>
            <div className="flex flex-wrap gap-2">
              {JURISDICTIONS.map(j => (
                <button key={j.value} onClick={() => toggle(jurs, j.value, setJurs)}
                  className={cn(
                    "text-xs px-2.5 py-1 rounded-lg border transition-all",
                    jurs.includes(j.value)
                      ? "bg-[rgba(0,212,170,0.1)] border-[rgba(0,212,170,0.4)] text-[#00d4aa]"
                      : "border-[#2a3040] text-[#4a5568]"
                  )}>
                  {j.flag} {j.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">Domains (empty = all)</p>
            <div className="flex flex-wrap gap-2">
              {DOMAINS.map(d => (
                <button key={d.value} onClick={() => toggle(doms, d.value, setDoms)}
                  className={cn(
                    "text-xs px-2.5 py-1 rounded-lg border transition-all",
                    doms.includes(d.value) ? "border-opacity-60" : "border-[#2a3040] text-[#4a5568]"
                  )}
                  style={doms.includes(d.value) ? {
                    background: d.bg, borderColor: `${d.color}60`, color: d.color
                  } : {}}>
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">Minimum Severity</p>
            <div className="flex gap-2">
              {["high", "medium", "low"].map(s => (
                <button key={s} onClick={() => setThresh(s)}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-lg border transition-all capitalize",
                    thresh === s
                      ? "bg-[rgba(0,212,170,0.1)] border-[rgba(0,212,170,0.4)] text-[#00d4aa]"
                      : "border-[#2a3040] text-[#4a5568]"
                  )}>
                  {s}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={() => onSave({ jurisdictions: jurs, domains: doms, severity_threshold: thresh, email_enabled: true })}
            disabled={saving}
            className="w-full py-2.5 rounded-xl bg-[#00d4aa] text-black font-bold text-sm flex items-center justify-center gap-2">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Bell size={14} />}
            {saving ? "Saving…" : "Save Subscription"}
          </button>
        </div>
      </div>
    </div>
  );
}
