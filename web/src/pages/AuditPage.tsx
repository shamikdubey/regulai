import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardList, ChevronLeft, ChevronRight, Loader2,
  Shield, Clock, X, ChevronDown,
} from "lucide-react";
import { api, AuditEntry } from "@/lib/api";
import { cn, confidenceLabel, formatLatency, JURISDICTION_MAP, DOMAIN_MAP } from "@/lib/utils";
import JurisdictionSelector from "@/components/features/JurisdictionSelector";
import DomainSelector from "@/components/features/DomainSelector";
import { useAppStore } from "@/stores/appStore";

const PAGE_SIZE = 25;

export default function AuditPage() {
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const { selectedJurisdiction, selectedDomain } = useAppStore();

  const auditQ = useQuery({
    queryKey: ["audit", page, selectedJurisdiction, selectedDomain],
    queryFn: () =>
      api.getAuditLog({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        jurisdiction: selectedJurisdiction || undefined,
        domain: selectedDomain || undefined,
      }),
  });

  const detailQ = useQuery({
    queryKey: ["audit-entry", selected],
    queryFn: () => api.getAuditEntry(selected!),
    enabled: !!selected,
  });

  const entries = auditQ.data || [];

  return (
    <div className="flex h-full">
      {/* List */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1f2530] flex items-center gap-4 flex-shrink-0">
          <div>
            <h1 className="font-serif text-xl text-[#e8ecf2]">Audit Log</h1>
            <p className="text-xs text-[#4a5568] mt-0.5">HMAC-signed, tamper-evident record of all AI queries</p>
          </div>
          <JurisdictionSelector />
          <DomainSelector />
          <div className="ml-auto flex items-center gap-1 text-xs text-[#00d4aa] font-mono">
            <Shield size={12} /> HMAC-verified
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-y-auto">
          {auditQ.isLoading ? (
            <div className="flex justify-center py-16">
              <Loader2 size={24} className="animate-spin text-[#4a5568]" />
            </div>
          ) : entries.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-[#4a5568]">
              <ClipboardList size={32} className="mb-3 opacity-40" />
              <p className="text-sm font-mono">No audit entries yet</p>
            </div>
          ) : (
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#0a0c10] border-b border-[#1f2530]">
                <tr>
                  {["Timestamp", "Query", "Jurisdiction", "Domain", "Confidence", "Latency"].map((h) => (
                    <th key={h} className="text-left px-5 py-3 text-[10px] font-mono text-[#4a5568] uppercase tracking-widest font-normal">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <AuditRow
                    key={entry.id}
                    entry={entry}
                    isSelected={selected === entry.id}
                    onClick={() => setSelected(selected === entry.id ? null : entry.id)}
                  />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-[#1f2530] flex-shrink-0">
          <span className="text-xs font-mono text-[#4a5568]">
            Page {page + 1} · {PAGE_SIZE} per page
          </span>
          <div className="flex items-center gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className={cn(
                "w-7 h-7 rounded-lg flex items-center justify-center transition-colors",
                page > 0
                  ? "bg-[#181c24] text-[#8892a4] hover:text-[#e8ecf2]"
                  : "text-[#2a3040] cursor-not-allowed"
              )}
            >
              <ChevronLeft size={14} />
            </button>
            <button
              disabled={entries.length < PAGE_SIZE}
              onClick={() => setPage((p) => p + 1)}
              className={cn(
                "w-7 h-7 rounded-lg flex items-center justify-center transition-colors",
                entries.length === PAGE_SIZE
                  ? "bg-[#181c24] text-[#8892a4] hover:text-[#e8ecf2]"
                  : "text-[#2a3040] cursor-not-allowed"
              )}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Detail panel */}
      <AnimatePresence>
        {selected && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 440, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-l border-[#1f2530] overflow-hidden flex-shrink-0"
          >
            <div className="w-[440px] h-full flex flex-col overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-[#1f2530]">
                <span className="text-xs font-mono text-[#4a5568] uppercase tracking-widest">Entry Detail</span>
                <button onClick={() => setSelected(null)} className="text-[#4a5568] hover:text-[#e8ecf2]">
                  <X size={14} />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-5">
                {detailQ.isLoading ? (
                  <Loader2 size={20} className="animate-spin text-[#4a5568] mx-auto mt-8" />
                ) : detailQ.data ? (
                  <AuditDetail entry={detailQ.data} />
                ) : null}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function AuditRow({
  entry, isSelected, onClick,
}: {
  entry: AuditEntry;
  isSelected: boolean;
  onClick: () => void;
}) {
  const conf = entry.confidence != null ? confidenceLabel(entry.confidence) : null;
  const j = entry.jurisdiction ? JURISDICTION_MAP[entry.jurisdiction] : null;
  const d = entry.domain ? DOMAIN_MAP[entry.domain] : null;

  return (
    <tr
      onClick={onClick}
      className={cn(
        "border-b border-[#1f2530] cursor-pointer transition-colors",
        isSelected ? "bg-[rgba(0,212,170,0.05)]" : "hover:bg-[#111318]"
      )}
    >
      <td className="px-5 py-3 text-[#4a5568] font-mono whitespace-nowrap">
        {new Date(entry.created_at).toLocaleString()}
      </td>
      <td className="px-5 py-3 text-[#8892a4] max-w-xs">
        <p className="truncate">{entry.query}</p>
      </td>
      <td className="px-5 py-3 text-[#8892a4]">
        {j ? `${j.flag} ${j.label}` : "—"}
      </td>
      <td className="px-5 py-3">
        {d ? (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
            style={{ color: d.color, background: d.bg, border: `1px solid ${d.color}40` }}>
            {entry.domain!.toUpperCase()}
          </span>
        ) : "—"}
      </td>
      <td className="px-5 py-3">
        {conf ? (
          <span className="font-mono" style={{ color: conf.color }}>
            {Math.round((entry.confidence ?? 0) * 100)}%
          </span>
        ) : "—"}
      </td>
      <td className="px-5 py-3 text-[#4a5568] font-mono">
        {entry.latency_ms != null ? formatLatency(entry.latency_ms) : "—"}
      </td>
    </tr>
  );
}

function AuditDetail({ entry }: { entry: any }) {
  const conf = entry.confidence != null ? confidenceLabel(entry.confidence) : null;

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-1.5">Query</div>
        <p className="text-sm text-[#e8ecf2] leading-relaxed">{entry.query}</p>
      </div>

      <div>
        <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-1.5">Response</div>
        <p className="text-xs text-[#8892a4] leading-relaxed whitespace-pre-wrap">{entry.response}</p>
      </div>

      {entry.citations?.length > 0 && (
        <div>
          <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">Citations</div>
          <div className="space-y-2">
            {entry.citations.map((c: any, i: number) => (
              <div key={i} className="px-3 py-2 rounded-lg bg-[#181c24] border border-[#2a3040]">
                <p className="text-xs font-semibold text-[#e8ecf2]">{c.regulation}</p>
                <p className="text-[10px] text-[#4a5568] font-mono mt-0.5">
                  {c.jurisdiction?.toUpperCase()} {c.year && `· ${c.year}`}
                  {c.section && ` · § ${c.section}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <MetaCard label="Confidence" value={conf ? `${Math.round(entry.confidence * 100)}%` : "—"} color={conf?.color} />
        <MetaCard label="Latency" value={entry.latency_ms != null ? formatLatency(entry.latency_ms) : "—"} />
        <MetaCard label="Jurisdiction" value={entry.jurisdiction?.toUpperCase() || "—"} />
        <MetaCard label="Domain" value={entry.domain?.toUpperCase() || "—"} />
      </div>

      <div>
        <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-1.5">HMAC Signature</div>
        <div className="px-3 py-2 rounded-lg bg-[#181c24] border border-[#1f2530]">
          <p className="text-[10px] font-mono text-[#4a5568] break-all">{entry.hmac_signature || "—"}</p>
        </div>
        <p className="text-[10px] text-[#4a5568] mt-1">SHA-256 HMAC — tamper detection for compliance records</p>
      </div>

      <div>
        <div className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-1">Timestamp</div>
        <p className="text-xs font-mono text-[#8892a4]">{new Date(entry.created_at).toISOString()}</p>
      </div>
    </div>
  );
}

function MetaCard({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="px-3 py-2.5 rounded-lg bg-[#181c24] border border-[#2a3040]">
      <div className="text-[9px] font-mono text-[#4a5568] uppercase tracking-widest mb-1">{label}</div>
      <div className="text-sm font-mono font-semibold" style={{ color: color || "#e8ecf2" }}>{value}</div>
    </div>
  );
}
