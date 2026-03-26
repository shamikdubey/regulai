import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Plus, X, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useJobPoller } from "@/hooks/useJobPoller";
import JobProgress from "@/components/features/JobProgress";
import { JURISDICTIONS, cn } from "@/lib/utils";

type GapItem = { jurisdiction:string; gap:string; requirement:string; risk_level:string; estimated_timeline:string; action_required:string };
type GapResult = { product_name:string; overall_risk:string; gaps:GapItem[]; summary:string; critical_path:string[]; estimated_total_months:number; latency_ms?:number };

const RISK_COLORS: Record<string, string> = { HIGH:"#ff4757", MEDIUM:"#f5a623", LOW:"#00d4aa" };
const PRODUCT_TYPES = ["food","pharma","device","nutra","ayurveda"];

export default function GapAssessmentPage() {
  const [productName, setProductName] = useState("");
  const [productType, setProductType] = useState("nutra");
  const [description, setDescription] = useState("");
  const [claims, setClaims] = useState("");
  const [jurisdictions, setJurisdictions] = useState<string[]>([]);
  const [currentApprovals, setCurrentApprovals] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string|null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [syncResult, setSyncResult] = useState<GapResult|null>(null);

  const job = useJobPoller<GapResult>(jobId);
  const result: GapResult | null = job.result || syncResult;

  const toggleJur = (v: string) => setJurisdictions(p => p.includes(v) ? p.filter(x=>x!==v) : [...p,v]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim() || jurisdictions.length === 0) { toast.error("Fill in product name and select at least one jurisdiction"); return; }
    setSubmitting(true); setSyncResult(null); setJobId(null);
    try {
      const resp = await getApiClient().post("/gap-assessment", {
        product_name: productName, product_description: description,
        product_type: productType, target_jurisdictions: jurisdictions,
        current_approvals: currentApprovals, intended_claims: claims,
      });
      if (resp.data.job_id) {
        setJobId(resp.data.job_id);
      } else {
        setSyncResult(resp.data);
      }
    } catch { toast.error("Failed to start gap assessment"); }
    finally { setSubmitting(false); }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6"><h1 className="text-xl font-bold text-[#e8ecf2]">Gap Assessment</h1>
        <p className="text-xs text-[#4a5568] mt-1">Identify compliance gaps across target markets</p></div>

      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Product name *</label>
            <input value={productName} onChange={e=>setProductName(e.target.value)} required
              placeholder="e.g. OmegaPlus Fish Oil Capsules"
              className="w-full px-3 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"/></div>
          <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Product type *</label>
            <select value={productType} onChange={e=>setProductType(e.target.value)}
              className="w-full px-3 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] capitalize">
              {PRODUCT_TYPES.map(t=><option key={t} value={t} className="capitalize">{t}</option>)}
            </select></div>
        </div>
        <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Product description</label>
          <textarea value={description} onChange={e=>setDescription(e.target.value)} rows={3}
            placeholder="Describe composition, intended use, dosage form..."
            className="w-full px-3 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors resize-none"/></div>
        <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Intended claims (optional)</label>
          <input value={claims} onChange={e=>setClaims(e.target.value)} placeholder="e.g. supports heart health, omega-3 supplement"
            className="w-full px-3 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"/></div>
        <div>
          <label className="block text-[10px] font-mono text-[#4a5568] mb-2 uppercase tracking-wider">Target jurisdictions * ({jurisdictions.length} selected)</label>
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto p-2 bg-[#111318] border border-[#2a3040] rounded-xl">
            {JURISDICTIONS.map(j=>(
              <button type="button" key={j.value} onClick={()=>toggleJur(j.value)}
                className={cn("flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all border",
                  jurisdictions.includes(j.value)
                    ? "bg-[rgba(0,212,170,0.12)] border-[rgba(0,212,170,0.4)] text-[#00d4aa]"
                    : "border-[#2a3040] text-[#4a5568] hover:border-[#4a5568] hover:text-[#8892a4]")}>
                <span>{j.flag}</span><span>{j.label}</span>
              </button>
            ))}
          </div>
        </div>
        <button type="submit" disabled={submitting||job.isRunning}
          className={cn("flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
            (submitting||job.isRunning)?"bg-[#1f2530] text-[#4a5568] cursor-not-allowed":"bg-[#00d4aa] text-black hover:bg-[#00bfa5] active:scale-[0.98]")}>
          {(submitting||job.isRunning)?<><Loader2 size={14} className="animate-spin"/>Running…</>:<><TrendingUp size={14}/>Run Gap Assessment</>}
        </button>
      </form>

      <JobProgress job={job} title="Running gap assessment…" estimatedSeconds={90} />

      <AnimatePresence>
        {result && (
          <motion.div initial={{opacity:0,y:16}} animate={{opacity:1,y:0}} className="space-y-4 mt-4">
            {/* Summary */}
            <div className="bg-[#111318] border border-[#1f2530] rounded-2xl p-5">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-bold text-[#e8ecf2]">{result.product_name}</h2>
                <span className="text-xs font-bold px-3 py-1 rounded-full" style={{background:`${RISK_COLORS[result.overall_risk]}20`,color:RISK_COLORS[result.overall_risk]}}>
                  {result.overall_risk} RISK
                </span>
              </div>
              <p className="text-sm text-[#8892a4] leading-relaxed">{result.summary}</p>
              <div className="flex gap-4 mt-3 text-[11px] text-[#4a5568] font-mono">
                <span>{result.gaps.length} gaps identified</span>
                <span>~{result.estimated_total_months} months to full compliance</span>
                {result.latency_ms && <span>{result.latency_ms}ms</span>}
              </div>
            </div>
            {/* Gaps */}
            {result.gaps.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-[#e8ecf2] uppercase tracking-wider">Compliance gaps</h3>
                {result.gaps.map((g,i)=>(
                  <div key={i} className="bg-[#111318] border border-[#1f2530] rounded-xl p-4" style={{borderLeftWidth:3,borderLeftColor:RISK_COLORS[g.risk_level]}}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-[#e8ecf2]">{g.jurisdiction.toUpperCase()}</span>
                      <span className="text-[10px] font-bold" style={{color:RISK_COLORS[g.risk_level]}}>{g.risk_level}</span>
                    </div>
                    <p className="text-xs font-semibold text-[#e8ecf2] mb-1">{g.gap}</p>
                    <p className="text-xs text-[#8892a4] mb-2">{g.requirement}</p>
                    <div className="flex items-center justify-between text-[10px] text-[#4a5568]">
                      <span>→ {g.action_required}</span>
                      <span className="font-mono">{g.estimated_timeline}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* Critical path */}
            {result.critical_path.length > 0 && (
              <div className="bg-[#111318] border border-[#1f2530] rounded-2xl p-5">
                <h3 className="text-xs font-bold text-[#e8ecf2] uppercase tracking-wider mb-3">Critical path</h3>
                {result.critical_path.map((s,i)=>(
                  <div key={i} className="flex items-start gap-3 mb-2">
                    <span className="w-5 h-5 rounded-full bg-[rgba(0,212,170,0.12)] text-[#00d4aa] text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i+1}</span>
                    <p className="text-xs text-[#8892a4]">{s}</p>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
