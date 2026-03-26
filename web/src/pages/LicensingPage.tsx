import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileCheck, Loader2, RefreshCw, ChevronRight, ExternalLink,
  Clock, AlertTriangle, CheckCircle, Zap, Shield
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn, JURISDICTIONS, JURISDICTION_MAP } from "@/lib/utils";

const PRODUCT_TYPES = [
  { value: "food",           label: "Food / FBO" },
  { value: "nutraceutical",  label: "Nutraceutical / Supplement" },
  { value: "medical_device", label: "Medical Device" },
  { value: "pharma",         label: "Pharmaceutical" },
  { value: "ayurveda",       label: "Ayurveda / ASU Drug" },
];

const COMPLEXITY_CONFIG = {
  LOW:    { color: "#00d4aa", bg: "rgba(0,212,170,0.1)",   border: "rgba(0,212,170,0.3)" },
  MEDIUM: { color: "#f5a623", bg: "rgba(245,166,35,0.1)",  border: "rgba(245,166,35,0.3)" },
  HIGH:   { color: "#ff4757", bg: "rgba(255,71,87,0.1)",   border: "rgba(255,71,87,0.3)" },
};

function useLicensing(jurisdiction: string, productType: string, complexity: string) {
  return useQuery({
    queryKey: ["licensing", jurisdiction, productType, complexity],
    queryFn: () => getApiClient().get("/api/v1/licensing-pathways", {
      params: {
        jurisdiction: jurisdiction || undefined,
        product_type: productType || undefined,
        complexity: complexity || undefined,
      }
    }).then(r => r.data),
  });
}

export default function LicensingPage() {
  const [jurisdiction, setSelectedJurisdiction] = useState("");
  const [productType, setProductType] = useState("");
  const [complexity, setComplexity] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [tab, setTab] = useState("steps");
  const qc = useQueryClient();

  const { data, isLoading } = useLicensing(jurisdiction, productType, complexity);
  const pathways: any[] = data || [];

  const seedMut = useMutation({
    mutationFn: () => getApiClient().post("/api/v1/licensing-pathways/seed").then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["licensing"] });
      toast.success("Licensing data seeded");
    },
  });

  const TABS = [
    { id: "steps",      label: "Pathway Steps" },
    { id: "prereqs",    label: "Prerequisites" },
    { id: "documents",  label: "Documents" },
    { id: "fees",       label: "Fees & Timeline" },
    { id: "gmp",        label: "GMP Requirements" },
    { id: "postapproval", label: "Post-Approval" },
  ];

  return (
    <div className="flex h-full">
      {/* Left panel — filters + list */}
      <div className="w-80 flex-shrink-0 border-r border-[#1f2530] overflow-y-auto bg-[#111318]">
        <div className="p-4 border-b border-[#1f2530]">
          <h2 className="font-serif text-base text-[#e8ecf2] mb-1">Licensing Navigator</h2>
          <p className="text-[10px] text-[#4a5568] leading-relaxed mb-4">
            Step-by-step licensing, registration and compliance pathways per country and product type
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">Jurisdiction</label>
              <select value={jurisdiction} onChange={e => { setSelectedJurisdiction(e.target.value); setSelected(null); }}
                className="w-full text-xs bg-[#181c24] border border-[#2a3040] text-[#e8ecf2] rounded-lg px-2.5 py-2 outline-none focus:border-[#00d4aa]">
                <option value="">All jurisdictions</option>
                {JURISDICTIONS.map(j => <option key={j.value} value={j.value}>{j.flag} {j.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">Product Type</label>
              <select value={productType} onChange={e => { setProductType(e.target.value); setSelected(null); }}
                className="w-full text-xs bg-[#181c24] border border-[#2a3040] text-[#e8ecf2] rounded-lg px-2.5 py-2 outline-none focus:border-[#00d4aa]">
                <option value="">All product types</option>
                {PRODUCT_TYPES.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">Complexity</label>
              <div className="flex gap-2">
                {["", "LOW", "MEDIUM", "HIGH"].map(c => {
                  const cfg = c ? COMPLEXITY_CONFIG[c as keyof typeof COMPLEXITY_CONFIG] : null;
                  return (
                    <button key={c} onClick={() => { setComplexity(c); setSelected(null); }}
                      className={cn("flex-1 text-[10px] font-mono py-1.5 rounded-lg border transition-all",
                        complexity === c
                          ? "text-[#e8ecf2] border-[#4a5568] bg-[#2a3040]"
                          : "text-[#4a5568] border-[#2a3040] hover:border-[#4a5568]"
                      )}
                      style={complexity === c && cfg ? { color: cfg.color, background: cfg.bg, borderColor: cfg.border } : {}}>
                      {c || "All"}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Pathway list */}
        {isLoading ? (
          <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-[#4a5568]" /></div>
        ) : pathways.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-[#4a5568] px-4">
            <FileCheck size={24} className="mb-2 opacity-30" />
            <p className="text-xs font-mono text-center mb-3">No pathways loaded</p>
            <button onClick={() => seedMut.mutate()} disabled={seedMut.isPending}
              className="text-xs text-[#00d4aa] flex items-center gap-1 hover:text-white transition-colors">
              {seedMut.isPending ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
              Load sample data
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[#1f2530]">
            {pathways.map((p: any) => {
              const j = JURISDICTION_MAP[p.jurisdiction];
              const pt = PRODUCT_TYPES.find(t => t.value === p.product_type);
              const cfg = COMPLEXITY_CONFIG[p.complexity as keyof typeof COMPLEXITY_CONFIG] || COMPLEXITY_CONFIG.MEDIUM;
              return (
                <button key={p.id} onClick={() => { setSelected(p); setTab("steps"); }}
                  className={cn("w-full text-left px-4 py-4 transition-colors hover:bg-[#181c24] flex items-start gap-2.5",
                    selected?.id === p.id && "bg-[rgba(0,212,170,0.06)]")}>
                  <span className="text-lg flex-shrink-0 mt-0.5">{j?.flag || "🌐"}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-[#e8ecf2] leading-snug">{j?.label} — {pt?.label || p.product_type}</p>
                    {p.product_subtype && <p className="text-[10px] text-[#4a5568] mt-0.5">{p.product_subtype.replace(/_/g," ")}</p>}
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                        style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                        {p.complexity}
                      </span>
                      {p.typical_timeline_months && (
                        <span className="text-[10px] text-[#4a5568] flex items-center gap-0.5">
                          <Clock size={9} /> {p.typical_timeline_months}
                        </span>
                      )}
                      {p.fast_track_available && (
                        <span className="text-[10px] text-[#00d4aa] flex items-center gap-0.5">
                          <Zap size={9} /> Fast track
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronRight size={12} className="text-[#4a5568] flex-shrink-0 mt-1" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Right — detail view */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-full text-[#4a5568]">
            <FileCheck size={40} className="mb-4 opacity-20" />
            <p className="text-sm font-mono">Select a jurisdiction and product type</p>
            <p className="text-xs mt-2 text-center max-w-xs leading-relaxed">
              Get step-by-step licensing pathway, fees, timelines, GMP requirements, and post-approval obligations
            </p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="px-6 py-4 border-b border-[#1f2530] flex-shrink-0">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{JURISDICTION_MAP[selected.jurisdiction]?.flag}</span>
                  <div>
                    <h2 className="font-serif text-lg text-[#e8ecf2] leading-snug">{selected.license_type}</h2>
                    <p className="text-xs text-[#4a5568] font-mono mt-0.5">{selected.competent_authority}</p>
                    <p className="text-[10px] text-[#4a5568] mt-1">{selected.reference_regulation}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 flex-shrink-0 ml-4">
                  {(() => {
                    const cfg = COMPLEXITY_CONFIG[selected.complexity as keyof typeof COMPLEXITY_CONFIG];
                    return (
                      <span className="text-xs font-mono px-2.5 py-1 rounded-lg"
                        style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}>
                        {selected.complexity} COMPLEXITY
                      </span>
                    );
                  })()}
                  {selected.fast_track_available && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[rgba(0,212,170,0.1)] text-[#00d4aa] border border-[rgba(0,212,170,0.3)] flex items-center gap-1">
                      <Zap size={9} /> Fast track available
                    </span>
                  )}
                  {selected.application_portal && (
                    <a href={selected.application_portal} target="_blank" rel="noopener noreferrer"
                      className="text-[10px] text-[#6699ff] flex items-center gap-1 hover:underline">
                      <ExternalLink size={9} /> Application portal
                    </a>
                  )}
                </div>
              </div>
            </div>

            {/* Tab bar */}
            <div className="flex border-b border-[#1f2530] flex-shrink-0 overflow-x-auto">
              {TABS.map(t => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={cn("px-4 py-2.5 text-[11px] font-mono font-semibold whitespace-nowrap tracking-wider border-b-2 transition-colors",
                    tab === t.id ? "text-[#00d4aa] border-[#00d4aa]" : "text-[#4a5568] border-transparent hover:text-[#8892a4]")}>
                  {t.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
              {tab === "steps" && (
                <div>
                  <div className="space-y-3 mb-6">
                    {(selected.pathway_steps || []).map((step: string, i: number) => (
                      <div key={i} className="flex items-start gap-3 p-4 rounded-xl bg-[#111318] border border-[#1f2530]">
                        <div className="w-6 h-6 rounded-full bg-[rgba(0,212,170,0.12)] border border-[rgba(0,212,170,0.3)] flex items-center justify-center flex-shrink-0 text-[10px] font-mono font-bold text-[#00d4aa]">
                          {i + 1}
                        </div>
                        <p className="text-xs text-[#8892a4] leading-relaxed pt-0.5">{step.replace(/^\d+\.\s*/, "")}</p>
                      </div>
                    ))}
                  </div>
                  {selected.fast_track_available && selected.fast_track_details && (
                    <div className="p-4 rounded-xl bg-[rgba(0,212,170,0.05)] border border-[rgba(0,212,170,0.2)]">
                      <p className="text-[10px] font-mono text-[#00d4aa] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Zap size={10} /> Fast Track Option
                      </p>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{selected.fast_track_details}</p>
                    </div>
                  )}
                  {selected.notes && (
                    <div className="mt-4 p-4 rounded-xl bg-[rgba(245,166,35,0.05)] border border-[rgba(245,166,35,0.2)]">
                      <p className="text-[10px] font-mono text-[#f5a623] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <AlertTriangle size={10} /> Important Notes
                      </p>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{selected.notes}</p>
                    </div>
                  )}
                </div>
              )}

              {tab === "prereqs" && (
                <div className="space-y-2">
                  <p className="text-xs text-[#4a5568] mb-4">These must be in place before submitting your application:</p>
                  {(selected.prerequisites || []).map((p: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg bg-[#111318] border border-[#1f2530]">
                      <CheckCircle size={13} className="text-[#f5a623] flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-[#8892a4] leading-relaxed">{p}</p>
                    </div>
                  ))}
                </div>
              )}

              {tab === "documents" && (
                <div className="space-y-2">
                  <p className="text-xs text-[#4a5568] mb-4">Documents to prepare and submit:</p>
                  {(selected.documents_required || []).map((d: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg bg-[#111318] border border-[#1f2530]">
                      <span className="text-[10px] font-mono text-[#6699ff] flex-shrink-0 mt-0.5 w-5 text-center">{i + 1}</span>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{d}</p>
                    </div>
                  ))}
                </div>
              )}

              {tab === "fees" && (
                <div className="space-y-5">
                  <div>
                    <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-3">Application Fees</p>
                    {selected.fees && Object.entries(selected.fees).map(([k, v]: [string, any]) => (
                      <div key={k} className="flex items-center justify-between py-2.5 border-b border-[#1f2530]">
                        <span className="text-xs text-[#8892a4]">{k}</span>
                        <span className="text-xs font-mono text-[#00d4aa]">{v}</span>
                      </div>
                    ))}
                  </div>
                  <div className="p-4 rounded-xl bg-[#111318] border border-[#1f2530]">
                    <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Clock size={10} /> Typical Timeline
                    </p>
                    <p className="text-sm font-semibold text-[#e8ecf2]">{selected.typical_timeline_months}</p>
                  </div>
                  {selected.renewal_period_years && (
                    <div className="p-4 rounded-xl bg-[#111318] border border-[#1f2530]">
                      <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-2">Renewal Period</p>
                      <p className="text-sm font-semibold text-[#e8ecf2]">Every {selected.renewal_period_years} year{selected.renewal_period_years > 1 ? "s" : ""}</p>
                      {selected.renewal_requirements?.length > 0 && (
                        <div className="mt-3 space-y-1.5">
                          {selected.renewal_requirements.map((r: string, i: number) => (
                            <p key={i} className="text-xs text-[#8892a4]">• {r}</p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {tab === "gmp" && selected.gmp_requirements && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-[rgba(102,153,255,0.05)] border border-[rgba(102,153,255,0.2)]">
                    <p className="text-[10px] font-mono text-[#6699ff] uppercase tracking-wider mb-3 flex items-center gap-1.5">
                      <Shield size={10} /> GMP Standard
                    </p>
                    <p className="text-sm font-semibold text-[#e8ecf2] mb-2">{selected.gmp_requirements.standard}</p>
                  </div>
                  {Object.entries(selected.gmp_requirements).filter(([k]) => k !== "standard").map(([k, v]: [string, any]) => (
                    <div key={k}>
                      <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-1.5 capitalize">{k.replace(/_/g," ")}</p>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{String(v)}</p>
                    </div>
                  ))}
                </div>
              )}

              {tab === "postapproval" && (
                <div className="space-y-2">
                  <p className="text-xs text-[#4a5568] mb-4">Ongoing obligations after licence is granted:</p>
                  {(selected.post_approval_obligations || []).map((o: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg bg-[#111318] border border-[#1f2530]">
                      <span className="text-[#a78bfa] flex-shrink-0 text-xs mt-0.5">→</span>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{o}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
