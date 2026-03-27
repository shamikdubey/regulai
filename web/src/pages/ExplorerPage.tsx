import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Search, ExternalLink, BookOpen } from "lucide-react";
import { api, RegulatoryBody, Regulation } from "@/lib/api";
import { useAppStore } from "@/stores/appStore";
import { cn, JURISDICTIONS, DOMAINS, DOMAIN_MAP, JURISDICTION_MAP } from "@/lib/utils";
import JurisdictionSelector from "@/components/features/JurisdictionSelector";
import DomainSelector from "@/components/features/DomainSelector";

export default function ExplorerPage() {
  const { selectedJurisdiction, selectedDomain } = useAppStore();
  const [activeTab, setActiveTab] = useState<"bodies" | "regulations">("bodies");
  const [search, setSearch] = useState("");

  const bodiesQ = useQuery({
    queryKey: ["bodies", selectedJurisdiction, selectedDomain],
    queryFn: () => api.getBodies({ jurisdiction: selectedJurisdiction || undefined, domain: selectedDomain || undefined }),
  });

  const regsQ = useQuery({
    queryKey: ["regulations", selectedJurisdiction, selectedDomain],
    queryFn: () => api.getRegulations({ jurisdiction: selectedJurisdiction || undefined, domain: selectedDomain || undefined }),
  });

  const filterText = (s: string) => s.toLowerCase().includes(search.toLowerCase());
  const bodies = (bodiesQ.data || []).filter((b) => filterText(b.name) || filterText(b.acronym));
  const regulations = (regsQ.data || []).filter((r) => filterText(r.name) || filterText(r.short_name || ""));

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#1f2530] flex items-center gap-4 flex-shrink-0">
        <div className="flex-1">
          <h1 className="font-serif text-xl text-[#e8ecf2]">Regulatory Explorer</h1>
          <p className="text-xs text-[#4a5568] mt-0.5">Browse bodies & regulations across all 10 jurisdictions</p>
        </div>
        <JurisdictionSelector />
        <DomainSelector />
      </div>

      {/* Tabs + Search */}
      <div className="flex items-center gap-0 border-b border-[#1f2530] px-6 flex-shrink-0">
        {(["bodies", "regulations"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-3 text-xs font-mono font-semibold tracking-wider uppercase border-b-2 transition-colors",
              activeTab === tab
                ? "border-[#00d4aa] text-[#00d4aa]"
                : "border-transparent text-[#4a5568] hover:text-[#8892a4]"
            )}
          >
            {tab === "bodies" ? `Bodies (${bodies.length})` : `Regulations (${regulations.length})`}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2 py-2">
          <Search size={14} className="text-[#4a5568]" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search…"
            className="bg-transparent text-sm text-[#e8ecf2] placeholder-[#4a5568] outline-none w-40"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "bodies" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {bodies.map((body) => <BodyCard key={body.id} body={body} />)}
            {bodies.length === 0 && <EmptyGrid />}
          </div>
        )}
        {activeTab === "regulations" && (
          <div className="space-y-3">
            {regulations.map((reg) => <RegulationRow key={reg.id} reg={reg} />)}
            {regulations.length === 0 && <EmptyGrid />}
          </div>
        )}
      </div>
    </div>
  );
}

function BodyCard({ body }: { body: RegulatoryBody }) {
  const j = JURISDICTION_MAP[body.jurisdiction];
  const primaryDomain = body.domains[0];
  const domainColor = DOMAIN_MAP[primaryDomain]?.color || "#8892a4";

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-[#111318] border border-[#1f2530] rounded-xl p-5 hover:border-[#2a3040] transition-all group"
      style={{ borderTopColor: domainColor, borderTopWidth: 2 }}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="font-mono text-sm font-semibold" style={{ color: domainColor }}>{body.acronym}</span>
        <div className="flex gap-1.5 flex-wrap justify-end">
          {body.domains.map((d) => (
            <span key={d} className="text-[9px] font-mono px-1.5 py-0.5 rounded"
              style={{ background: DOMAIN_MAP[d]?.bg, color: DOMAIN_MAP[d]?.color, border: `1px solid ${DOMAIN_MAP[d]?.color}40` }}>
              {d.toUpperCase()}
            </span>
          ))}
        </div>
      </div>
      <h3 className="text-sm font-bold text-[#e8ecf2] mb-2 leading-snug">{body.name}</h3>
      <p className="text-xs text-[#8892a4] leading-relaxed mb-4 line-clamp-3">{body.description}</p>
      <div className="flex items-center gap-3 text-[10px] font-mono text-[#4a5568]">
        <span>{j?.flag} {j?.label}</span>
        {body.established_year && <span>Est. {body.established_year}</span>}
        {body.website && (
          <a
            onClick={() => windows.open(`https://${body.website}`, "_blank")}
            className="ml-auto flex items-center gap-1 text-[#4a5568] hover:text-[#00d4aa] cursor-pointer transition-colors"
          >
            <ExternalLink size={10} /> {body.website}
          </a>
        )}
      </div>
    </motion.div>
  );
}

function RegulationRow({ reg }: { reg: Regulation }) {
  const [expanded, setExpanded] = useState(false);
  const j = JURISDICTION_MAP[reg.jurisdiction];
  const d = DOMAIN_MAP[reg.domain];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="bg-[#111318] border border-[#1f2530] rounded-xl px-5 py-4 hover:border-[#2a3040] transition-all"
    >
      <div className="flex items-start gap-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <BookOpen size={16} className="text-[#4a5568] mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-1">
            <h3 className="text-sm font-bold text-[#e8ecf2]">{reg.name}</h3>
            {reg.short_name && <span className="text-[10px] font-mono text-[#4a5568]">({reg.short_name})</span>}
          </div>
          <div className="flex items-center gap-3 text-[10px] font-mono">
            <span>{j?.flag} {j?.label}</span>
            <span style={{ color: d?.color }}>{reg.domain.toUpperCase()}</span>
            {reg.year && <span className="text-[#4a5568]">{reg.year}</span>}
            <span className={cn("px-1.5 py-0.5 rounded", reg.status === "active" ? "text-[#00d4aa] bg-[rgba(0,212,170,0.08)]" : "text-[#4a5568]")}>
              {reg.status}
            </span>
          </div>
        </div>
      </div>
      {expanded && reg.description && (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="text-xs text-[#8892a4] leading-relaxed mt-3 ml-7"
        >
          {reg.description}
        </motion.p>
      )}
    </motion.div>
  );
}

function EmptyGrid() {
  return (
    <div className="col-span-full flex flex-col items-center py-16 text-[#4a5568]">
      <Search size={32} className="mb-3 opacity-40" />
      <p className="text-sm font-mono">No results — try adjusting filters</p>
    </div>
  );
}
