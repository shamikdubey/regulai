import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, ChevronDown, ChevronUp, FlaskConical, RefreshCw } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

const PHARMA_SOURCES = ["USP","EP","BP","IP","JP","ChP","NF","FCC","JECFA","FSSAI","AYUSH","WHO","IS"];
const CATEGORIES = ["All","vitamin","mineral","botanical","food additive","excipient","API"];
const DOMAINS = [
  { value: "All",            label: "All Domains" },
  { value: "food",           label: "Food & Food Additives" },
  { value: "pharma",         label: "Pharmaceuticals/APIs" },
  { value: "nutra",          label: "Nutraceuticals/Supplements" },
  { value: "ayurveda",       label: "Ayurveda/Traditional Medicine" },
];

function useIngredientSpecs(params: Record<string,string>) {
  return useQuery({
    queryKey: ["ingredient-specs", params],
    queryFn: () => getApiClient().get("/api/v1/ingredient-specs", { params }).then(r => r.data),
  });
}

function useSeedSpecs() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => getApiClient().post("/api/v1/ingredient-specs/seed").then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ingredient-specs"] }); toast.success("Specifications seeded"); },
  });
}

export default function IngredientSpecsPage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [domain, setSelectedDomain] = useState("All");
  const [selected, setSelected] = useState<any>(null);
  const [activeTab, setActiveTab] = useState("assay");

  const params: Record<string,string> = {};
  if (search) params.search = search;
  if (category !== "All") params.category = category;
  if (domain !== "All") params.domain = domain;

  const specsQ = useIngredientSpecs(params);
  const seedMut = useSeedSpecs();
  const specs = specsQ.data || [];

  const DOMAIN_COLORS: Record<string,string> = { food:"#f5a623", pharma:"#00d4aa", nutra:"#a78bfa", ayurveda:"#ff6b35" };
  const CAT_COLORS: Record<string,string> = { vitamin:"#00d4aa", mineral:"#6699ff", botanical:"#ff6b35", "food additive":"#f5a623", excipient:"#8892a4", API:"#a78bfa" };

  return (
    <div className="flex h-full">
      {/* List panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="px-6 py-4 border-b border-[#1f2530] flex items-center gap-4 flex-shrink-0">
          <div>
            <h1 className="font-serif text-xl text-[#e8ecf2]">Ingredient Specifications</h1>
            <p className="text-xs text-[#4a5568] mt-0.5">Pharmacopoeial standards — USP · EP · IP · BP · JP · FCC · JECFA · FSSAI · IS</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#4a5568]" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Name, CAS, INS..."
                className="pl-8 pr-3 py-1.5 rounded-lg bg-[#111318] border border-[#2a3040] text-xs text-[#e8ecf2] placeholder-[#4a5568] outline-none focus:border-[#00d4aa] w-48 transition-colors" />
            </div>
            <select value={category} onChange={e => setCategory(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
            <select value={domain} onChange={e => setSelectedDomain(e.target.value)}
              className="text-xs bg-[#111318] border border-[#2a3040] text-[#8892a4] rounded-lg px-2 py-1.5 outline-none focus:border-[#00d4aa]">
              {DOMAINS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
            </select>
            {specs.length === 0 && !specsQ.isLoading && (
              <button onClick={() => seedMut.mutate()} disabled={seedMut.isPending}
                className="flex items-center gap-1 text-xs font-mono text-[#00d4aa] hover:text-white transition-colors">
                {seedMut.isPending ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />} Load data
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {specsQ.isLoading ? (
            <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-[#4a5568]" /></div>
          ) : specs.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-[#4a5568]">
              <FlaskConical size={32} className="mb-3 opacity-30" />
              <p className="text-sm font-mono">No specifications loaded</p>
              <button onClick={() => seedMut.mutate()} className="mt-3 text-xs text-[#00d4aa] hover:underline">Load sample data</button>
            </div>
          ) : (
            <div className="divide-y divide-[#1f2530]">
              {specs.map((s: any) => (
                <div key={s.id} onClick={() => setSelected(selected?.id === s.id ? null : s)}
                  className={cn("px-6 py-4 cursor-pointer transition-colors hover:bg-[#111318]", selected?.id === s.id && "bg-[rgba(0,212,170,0.04)]")}>
                  <div className="flex items-start gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-sm font-semibold text-[#e8ecf2]">{s.name}</span>
                        {s.cas_number && <span className="text-[10px] font-mono text-[#4a5568]">CAS: {s.cas_number}</span>}
                        {s.ins_number && <span className="text-[10px] font-mono text-[#4a5568]">INS: {s.ins_number}</span>}
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                          style={{ color: CAT_COLORS[s.category] || "#8892a4", background: `${CAT_COLORS[s.category] || "#8892a4"}15`, border: `1px solid ${CAT_COLORS[s.category] || "#8892a4"}40` }}>
                          {s.category}
                        </span>
                        <span className="text-[10px] font-mono" style={{ color: DOMAIN_COLORS[s.domain] || "#8892a4" }}>{s.domain.toUpperCase()}</span>
                        {s.pharmacopoeias?.map((p: any) => (
                          <span key={p.source} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[#181c24] border border-[#2a3040] text-[#4a5568]">{p.source}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Detail panel */}
      <AnimatePresence>
        {selected && (
          <motion.div initial={{ width: 0, opacity: 0 }} animate={{ width: 520, opacity: 1 }} exit={{ width: 0, opacity: 0 }}
            className="border-l border-[#1f2530] flex-shrink-0 overflow-hidden">
            <div className="w-[520px] h-full flex flex-col overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1f2530] flex-shrink-0">
                <div>
                  <h3 className="text-sm font-semibold text-[#e8ecf2] leading-snug">{selected.name}</h3>
                  <p className="text-[10px] text-[#4a5568] font-mono mt-0.5">{selected.molecular_formula} · MW: {selected.molecular_weight}</p>
                </div>
                <button onClick={() => setSelected(null)} className="text-[#4a5568] hover:text-[#e8ecf2] text-xs">✕</button>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-[#1f2530] flex-shrink-0">
                {["assay","limits","pharmacopoeias","identity","storage"].map(t => (
                  <button key={t} onClick={() => setActiveTab(t)}
                    className={cn("px-4 py-2.5 text-[11px] font-mono font-semibold uppercase tracking-wider transition-colors border-b-2",
                      activeTab === t ? "text-[#00d4aa] border-[#00d4aa]" : "text-[#4a5568] border-transparent hover:text-[#8892a4]")}>
                    {t}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto p-5">
                {activeTab === "assay" && (
                  <div className="space-y-4">
                    <Section label="Assay Limits by Standard">
                      {selected.assay_limits && Object.entries(selected.assay_limits).map(([std, val]: [string, any]) => (
                        <KV key={std} label={std} value={String(val)} highlight />
                      ))}
                    </Section>
                    {selected.fssai_schedule && <Section label="FSSAI Schedule"><p className="text-xs text-[#8892a4]">{selected.fssai_schedule}</p></Section>}
                    {selected.codex_standard && <Section label="Codex Standard"><p className="text-xs text-[#8892a4]">{selected.codex_standard}</p></Section>}
                    {selected.jecfa_id && <Section label="JECFA Reference"><p className="text-xs text-[#8892a4]">{selected.jecfa_id}</p></Section>}
                  </div>
                )}
                {activeTab === "limits" && (
                  <div className="space-y-4">
                    <Section label="Heavy Metal Limits">
                      {selected.heavy_metal_limits && Object.entries(selected.heavy_metal_limits).map(([m, v]: any) => (
                        <KV key={m} label={m} value={v} />
                      ))}
                    </Section>
                    <Section label="Microbiological Limits">
                      {selected.microbiological_limits && Object.entries(selected.microbiological_limits).map(([m, v]: any) => (
                        <KV key={m} label={m} value={v} />
                      ))}
                    </Section>
                    <Section label="Impurity Limits">
                      {selected.impurity_limits && Object.entries(selected.impurity_limits).map(([m, v]: any) => (
                        <KV key={m} label={m} value={v} />
                      ))}
                    </Section>
                  </div>
                )}
                {activeTab === "pharmacopoeias" && (
                  <div className="space-y-3">
                    {(selected.pharmacopoeias || []).map((p: any) => (
                      <div key={p.source} className="p-3 rounded-xl bg-[#181c24] border border-[#2a3040]">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-[#00d4aa]">{p.source}</span>
                          <span className="text-[10px] font-mono text-[#4a5568]">{p.grade}</span>
                        </div>
                        <p className="text-xs text-[#8892a4] mb-1">{p.monograph_ref}</p>
                        <p className="text-xs text-[#e8ecf2] font-mono">Assay: {p.assay}</p>
                      </div>
                    ))}
                  </div>
                )}
                {activeTab === "identity" && (
                  <div className="space-y-3">
                    {selected.description && <Section label="Description"><p className="text-xs text-[#8892a4] leading-relaxed">{selected.description}</p></Section>}
                    {selected.appearance && <Section label="Appearance"><p className="text-xs text-[#8892a4]">{selected.appearance}</p></Section>}
                    {selected.solubility && <Section label="Solubility"><p className="text-xs text-[#8892a4] leading-relaxed">{selected.solubility}</p></Section>}
                    {selected.synonyms?.length > 0 && (
                      <Section label="Synonyms">
                        <div className="flex flex-wrap gap-1.5">
                          {selected.synonyms.map((s: string) => (
                            <span key={s} className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#181c24] border border-[#2a3040] text-[#4a5568]">{s}</span>
                          ))}
                        </div>
                      </Section>
                    )}
                  </div>
                )}
                {activeTab === "storage" && (
                  <div className="space-y-3">
                    {selected.storage && <Section label="Storage Conditions"><p className="text-sm text-[#8892a4] leading-relaxed">{selected.storage}</p></Section>}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-2">{label}</p>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function KV({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 border-b border-[#1f2530]">
      <span className="text-xs text-[#8892a4] leading-snug flex-1">{label}</span>
      <span className={cn("text-xs font-mono text-right flex-shrink-0", highlight ? "text-[#00d4aa]" : "text-[#e8ecf2]")}>{value}</span>
    </div>
  );
}
