import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Tag, Loader2, RefreshCw, ChevronRight, Check, AlertTriangle, Info } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn, JURISDICTIONS, JURISDICTION_MAP } from "@/lib/utils";

const PRODUCT_TYPES = [
  { value: "packaged_food", label: "Packaged Food" },
  { value: "nutraceutical", label: "Nutraceutical / Health Supplement" },
  { value: "ayurvedic_drug", label: "Ayurvedic Drug" },
  { value: "food_with_function_claims", label: "Food with Function Claims (Japan)" },
  { value: "complementary_medicine", label: "Complementary Medicine (AU)" },
];

function useLabelingReqs(jurisdiction: string, productType: string) {
  return useQuery({
    queryKey: ["labeling", jurisdiction, productType],
    queryFn: () => getApiClient().get("/api/v1/labeling-requirements", {
      params: { jurisdiction: jurisdiction || undefined, product_type: productType || undefined }
    }).then(r => r.data),
  });
}

export default function LabelingPage() {
  const [jurisdiction, setSelectedJurisdiction] = useState("");
  const [productType, setProductType] = useState("");
  const [selected, setSelected] = useState<any>(null);
  const [tab, setTab] = useState("mandatory");
  const qc = useQueryClient();

  const reqs: any[] = useLabelingReqs(jurisdiction, productType).data || [];
  const isLoading = useLabelingReqs(jurisdiction, productType).isLoading;

  const seedMut = useMutation({
    mutationFn: () => getApiClient().post("/api/v1/labeling-requirements/seed").then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["labeling"] }); toast.success("Labeling data seeded"); },
  });

  const SECTION_TABS = [
    { id: "mandatory", label: "Mandatory Fields" },
    { id: "nutrition", label: "Nutrition Declaration" },
    { id: "allergens", label: "Allergen Rules" },
    { id: "weights", label: "Weights & Measures" },
    { id: "claims", label: "Claims" },
    { id: "special", label: "Special Requirements" },
  ];

  return (
    <div className="flex h-full">
      {/* Left: filter + list */}
      <div className="w-72 flex-shrink-0 border-r border-[#1f2530] overflow-y-auto bg-[#111318]">
        <div className="p-4 border-b border-[#1f2530]">
          <h2 className="font-serif text-base text-[#e8ecf2] mb-1">Labeling Requirements</h2>
          <p className="text-[10px] text-[#4a5568] leading-relaxed mb-4">Country-specific label compliance rules by product type</p>

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
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8"><Loader2 size={20} className="animate-spin text-[#4a5568]" /></div>
        ) : reqs.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-[#4a5568] px-4">
            <Tag size={24} className="mb-2 opacity-30" />
            <p className="text-xs font-mono text-center mb-3">No labeling data</p>
            <button onClick={() => seedMut.mutate()} className="text-xs text-[#00d4aa] flex items-center gap-1 hover:text-white transition-colors">
              <RefreshCw size={10} /> Load sample data
            </button>
          </div>
        ) : (
          <div className="divide-y divide-[#1f2530]">
            {reqs.map((r: any) => {
              const j = JURISDICTION_MAP[r.jurisdiction];
              const pt = PRODUCT_TYPES.find(p => p.value === r.product_type);
              return (
                <button key={r.id} onClick={() => { setSelected(r); setTab("mandatory"); }}
                  className={cn("w-full text-left px-4 py-3.5 transition-colors hover:bg-[#181c24] flex items-start gap-2.5",
                    selected?.id === r.id && "bg-[rgba(0,212,170,0.06)]")}>
                  <span className="text-lg flex-shrink-0">{j?.flag || "🌐"}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-[#e8ecf2] leading-snug">{j?.label || r.jurisdiction}</p>
                    <p className="text-[10px] text-[#4a5568] mt-0.5 leading-snug">{pt?.label || r.product_type}</p>
                    <p className="text-[10px] text-[#4a5568] mt-1 font-mono">{r.competent_authority}</p>
                  </div>
                  <ChevronRight size={12} className="text-[#4a5568] flex-shrink-0 mt-1" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Right: detail */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {!selected ? (
          <div className="flex flex-col items-center justify-center h-full text-[#4a5568]">
            <Tag size={40} className="mb-4 opacity-20" />
            <p className="text-sm font-mono">Select a jurisdiction + product type</p>
          </div>
        ) : (
          <>
            <div className="px-6 py-4 border-b border-[#1f2530] flex-shrink-0">
              <div className="flex items-center gap-3 mb-1">
                <span className="text-2xl">{JURISDICTION_MAP[selected.jurisdiction]?.flag}</span>
                <div>
                  <h2 className="font-serif text-lg text-[#e8ecf2]">
                    {JURISDICTION_MAP[selected.jurisdiction]?.label} — {PRODUCT_TYPES.find(p => p.value === selected.product_type)?.label || selected.product_type}
                  </h2>
                  <p className="text-xs text-[#4a5568] font-mono mt-0.5">{selected.regulatory_basis}</p>
                </div>
              </div>
            </div>

            {/* Tab bar */}
            <div className="flex border-b border-[#1f2530] flex-shrink-0 overflow-x-auto">
              {SECTION_TABS.map(t => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={cn("px-4 py-2.5 text-[11px] font-mono font-semibold whitespace-nowrap tracking-wider border-b-2 transition-colors",
                    tab === t.id ? "text-[#00d4aa] border-[#00d4aa]" : "text-[#4a5568] border-transparent hover:text-[#8892a4]")}>
                  {t.label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-6 max-w-3xl">
              {tab === "mandatory" && (
                <div>
                  <p className="text-xs text-[#4a5568] mb-4">All fields below are legally required on the product label in {JURISDICTION_MAP[selected.jurisdiction]?.label}.</p>
                  <div className="space-y-2">
                    {(selected.mandatory_fields || []).map((f: string, i: number) => (
                      <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg bg-[#111318] border border-[#1f2530]">
                        <Check size={13} className="text-[#00d4aa] flex-shrink-0 mt-0.5" />
                        <p className="text-xs text-[#8892a4] leading-relaxed">{f}</p>
                      </div>
                    ))}
                  </div>
                  {selected.enforcement_notes && (
                    <div className="mt-4 p-4 rounded-xl bg-[rgba(102,153,255,0.05)] border border-[rgba(102,153,255,0.2)]">
                      <p className="text-[10px] font-mono text-[#6699ff] uppercase tracking-wider mb-2 flex items-center gap-1"><Info size={10} /> Enforcement</p>
                      <p className="text-xs text-[#8892a4] leading-relaxed">{selected.enforcement_notes}</p>
                    </div>
                  )}
                </div>
              )}

              {tab === "nutrition" && selected.nutrition_declaration && (
                <div className="space-y-4">
                  <DictSection data={selected.nutrition_declaration} highlight={["mandatory_nutrients","format","nrv_reference"]} />
                </div>
              )}

              {tab === "allergens" && selected.allergen_rules && (
                <div className="space-y-4">
                  <div>
                    <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-widest mb-3">Allergens requiring declaration</p>
                    <div className="flex flex-wrap gap-2">
                      {(selected.allergen_rules.top_allergens || []).map((a: string) => (
                        <span key={a} className="text-xs px-2.5 py-1 rounded-lg bg-[rgba(255,71,87,0.08)] border border-[rgba(255,71,87,0.2)] text-[#ff9999]">{a}</span>
                      ))}
                    </div>
                  </div>
                  {selected.allergen_rules.declaration_method && (
                    <InfoBox label="Declaration Method" value={selected.allergen_rules.declaration_method} />
                  )}
                  {selected.allergen_rules.regulatory_basis && (
                    <InfoBox label="Regulatory Basis" value={selected.allergen_rules.regulatory_basis} />
                  )}
                  {selected.allergen_rules.note && (
                    <div className="p-3 rounded-lg bg-[rgba(245,166,35,0.06)] border border-[rgba(245,166,35,0.2)]">
                      <p className="text-xs text-[#8892a4]">{selected.allergen_rules.note}</p>
                    </div>
                  )}
                </div>
              )}

              {tab === "weights" && selected.weights_measures && (
                <DictSection data={selected.weights_measures} />
              )}

              {tab === "claims" && (
                <div className="space-y-5">
                  {selected.prohibited_claims?.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-[#ff4757] uppercase tracking-widest mb-3 flex items-center gap-1"><AlertTriangle size={10} /> Prohibited Claims</p>
                      <div className="space-y-2">
                        {selected.prohibited_claims.map((c: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-[rgba(255,71,87,0.05)] border border-[rgba(255,71,87,0.15)]">
                            <span className="text-[#ff4757] text-xs flex-shrink-0">✕</span>
                            <p className="text-xs text-[#8892a4]">{c}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selected.claim_rules && (
                    <div>
                      <p className="text-[10px] font-mono text-[#00d4aa] uppercase tracking-widest mb-3">Permitted Claim Thresholds</p>
                      <div className="space-y-2">
                        {Object.entries(selected.claim_rules).map(([k, v]: [string, any]) => (
                          <div key={k} className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-[#111318] border border-[#1f2530]">
                            <span className="text-[10px] font-mono text-[#00d4aa] capitalize min-w-[120px] flex-shrink-0">{k.replace(/_/g," ")}</span>
                            <p className="text-xs text-[#8892a4]">{v}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {tab === "special" && (selected.special_requirements?.length > 0 || selected.language_requirements) && (
                <div className="space-y-4">
                  {selected.language_requirements && (
                    <div>
                      <p className="text-[10px] font-mono text-[#6699ff] uppercase tracking-widest mb-3">Language Requirements</p>
                      <DictSection data={selected.language_requirements} />
                    </div>
                  )}
                  {selected.special_requirements?.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-[#f5a623] uppercase tracking-widest mb-3">Special Requirements</p>
                      <div className="space-y-2">
                        {selected.special_requirements.map((r: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-[rgba(245,166,35,0.05)] border border-[rgba(245,166,35,0.15)]">
                            <span className="text-[#f5a623] text-xs flex-shrink-0 mt-0.5">!</span>
                            <p className="text-xs text-[#8892a4] leading-relaxed">{r}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">{label}</p>
      <p className="text-xs text-[#8892a4] leading-relaxed">{value}</p>
    </div>
  );
}

function DictSection({ data, highlight = [] }: { data: Record<string,any>; highlight?: string[] }) {
  return (
    <div className="space-y-3">
      {Object.entries(data).map(([k, v]) => {
        if (Array.isArray(v)) return (
          <div key={k}>
            <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-2">{k.replace(/_/g," ")}</p>
            <div className="flex flex-wrap gap-1.5">
              {v.map((i: string) => <span key={i} className="text-[10px] px-2 py-0.5 rounded bg-[#181c24] border border-[#2a3040] text-[#8892a4]">{i}</span>)}
            </div>
          </div>
        );
        if (typeof v === "object" && v !== null) return null;
        return (
          <div key={k} className="flex items-start gap-3 py-2 border-b border-[#1f2530]">
            <span className={cn("text-[10px] font-mono min-w-[140px] flex-shrink-0 capitalize", highlight.includes(k) ? "text-[#00d4aa]" : "text-[#4a5568]")}>
              {k.replace(/_/g," ")}
            </span>
            <span className="text-xs text-[#8892a4] leading-relaxed">{String(v)}</span>
          </div>
        );
      })}
    </div>
  );
}
