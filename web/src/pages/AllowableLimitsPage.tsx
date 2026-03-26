import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Search, Loader2, AlertTriangle, BarChart2, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn, JURISDICTIONS, JURISDICTION_MAP } from "@/lib/utils";

const LIMIT_TYPES = ["All","additive","contaminant","pesticide","microbiological","nutrient_rv"];
const CATEGORIES = ["All","preservative","colour","heavy_metal","mycotoxin","pathogen","indicator","organophosphate","herbicide","mineral","vitamin"];

function useAllowableLimits(params: Record<string,string>) {
  return useQuery({
    queryKey: ["allowable-limits", params],
    queryFn: () => getApiClient().get("/api/v1/allowable-limits", { params }).then(r => r.data),
  });
}

const SEVERITY: Record<string, string> = {
  "PROHIBITED": "#ff4757",
  "absent": "#ff4757",
  "Absent": "#ff4757",
};

function getSeverityColor(val: string): string {
  if (val === "PROHIBITED" || val.toLowerCase() === "absent") return "#ff4757";
  if (val === "GMP" || val.toLowerCase().includes("gmp")) return "#6699ff";
  const num = parseFloat(val);
  if (!isNaN(num)) {
    if (num <= 0.1) return "#ff4757";
    if (num <= 1) return "#f5a623";
    return "#00d4aa";
  }
  return "#8892a4";
}

export default function AllowableLimitsPage() {
  const [search, setSearch] = useState("");
  const [jurisdiction, setSelectedJurisdiction] = useState("");
  const [limitType, setLimitType] = useState("All");
  const [selected, setSelected] = useState<any>(null);
  const qc = useQueryClient();

  const params: Record<string,string> = {};
  if (search) params.substance = search;
  if (jurisdiction) params.jurisdiction = jurisdiction;
  if (limitType !== "All") params.limit_type = limitType;

  const limitsQ = useAllowableLimits(params);
  const seedMut = useMutation({
    mutationFn: () => getApiClient().post("/api/v1/allowable-limits/seed").then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["allowable-limits"] }); toast.success("Limits data seeded"); },
  });

  const limits: any[] = limitsQ.data || [];

  // Group by substance for comparison view
  const bySubstance: Record<string, any[]> = {};
  limits.forEach(l => {
    if (!bySubstance[l.substance]) bySubstance[l.substance] = [];
    bySubstance[l.substance].push(l);
  });

  const TYPE_COLORS: Record<string,string> = {
    additive:"#00d4aa", contaminant:"#ff4757", pesticide:"#f5a623",
    microbiological:"#a78bfa", nutrient_rv:"#6699ff"
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#1f2530] flex items-center gap-4 flex-shrink-0 flex-wrap">
          <div>
            <h1 className="font-serif text-xl text-[#e8ecf2]">Allowable Limits</h1>
            <p className="text-xs text-[#4a5568] mt-0.5">MRLs · ADIs · Contaminants · Additives · Microbiological · Nutrient RVs</p>
          </div>
          <div className="ml-auto flex items-center gap-2 flex-wrap">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#4a5568]" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Substance name..."
                className="pl-8 pr-3 py-1.5 rounded-lg bg-[#111318] border border-[#2a3040] text-xs text-[#e8ecf2] placeholder-[#4a5568] outline-none focus:border-[#00d4aa] w-44 transition-colors" />
            </div>
            <select value={jurisdiction} onChange={e => setSelectedJurisdiction(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              <option value="">All jurisdictions</option>
              {JURISDICTIONS.map(j => <option key={j.value} value={j.value}>{j.flag} {j.label}</option>)}
            </select>
            <select value={limitType} onChange={e => setLimitType(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              {LIMIT_TYPES.map(t => <option key={t}>{t}</option>)}
            </select>
            {limits.length === 0 && !limitsQ.isLoading && (
              <button onClick={() => seedMut.mutate()} disabled={seedMut.isPending}
                className="flex items-center gap-1 text-xs font-mono text-[#00d4aa] hover:text-white transition-colors">
                {seedMut.isPending ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />} Load data
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {limitsQ.isLoading ? (
            <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-[#4a5568]" /></div>
          ) : limits.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-[#4a5568]">
              <BarChart2 size={32} className="mb-3 opacity-30" />
              <p className="text-sm font-mono">No limits data loaded</p>
              <button onClick={() => seedMut.mutate()} className="mt-3 text-xs text-[#00d4aa] hover:underline">Load sample data</button>
            </div>
          ) : (
            <div className="p-6">
              {Object.entries(bySubstance).map(([substance, entries]) => (
                <div key={substance} className="mb-6">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="text-sm font-semibold text-[#e8ecf2]">{substance}</h3>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                      style={{ color: TYPE_COLORS[entries[0].limit_type] || "#8892a4",
                        background: `${TYPE_COLORS[entries[0].limit_type] || "#8892a4"}15`,
                        border: `1px solid ${TYPE_COLORS[entries[0].limit_type] || "#8892a4"}40` }}>
                      {entries[0].limit_type}
                    </span>
                    {entries[0].cas_number && <span className="text-[10px] font-mono text-[#4a5568]">CAS {entries[0].cas_number}</span>}
                    {entries[0].ins_number && <span className="text-[10px] font-mono text-[#4a5568]">INS {entries[0].ins_number}</span>}
                  </div>

                  <div className="grid grid-cols-1 gap-2">
                    {entries.map((e: any) => {
                      const j = JURISDICTION_MAP[e.jurisdiction] || { flag: "🌐", label: e.jurisdiction };
                      const col = getSeverityColor(e.limit_value);
                      return (
                        <div key={e.id} onClick={() => setSelected(selected?.id === e.id ? null : e)}
                          className={cn("flex items-center gap-3 px-4 py-3 rounded-xl bg-[#111318] border cursor-pointer transition-all hover:border-[#2a3040]",
                            selected?.id === e.id ? "border-[rgba(0,212,170,0.3)]" : "border-[#1f2530]")}>
                          <span className="text-base flex-shrink-0">{j.flag}</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[#8892a4] truncate">{e.food_matrix}</p>
                            <p className="text-[10px] text-[#4a5568] font-mono mt-0.5">{e.regulatory_basis}</p>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="text-sm font-mono font-semibold" style={{ color: col }}>
                              {e.limit_value}
                            </p>
                            <p className="text-[10px] text-[#4a5568]">{e.limit_unit}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Expanded detail */}
                  {selected && entries.find((e: any) => e.id === selected.id) && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
                      className="mt-2 px-4 py-4 rounded-xl bg-[#0a0c10] border border-[#2a3040] space-y-3">
                      {selected.adi_tdi && (
                        <div>
                          <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">ADI / TDI</p>
                          <p className="text-xs text-[#f5a623]">{selected.adi_tdi}</p>
                        </div>
                      )}
                      {selected.notes && (
                        <div>
                          <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">Notes</p>
                          <p className="text-xs text-[#8892a4] leading-relaxed">{selected.notes}</p>
                        </div>
                      )}
                      {selected.limit_value === "PROHIBITED" && (
                        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[rgba(255,71,87,0.08)] border border-[rgba(255,71,87,0.2)]">
                          <AlertTriangle size={12} className="text-[#ff4757]" />
                          <p className="text-xs text-[#ff4757]">This substance is PROHIBITED in this jurisdiction</p>
                        </div>
                      )}
                    </motion.div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
