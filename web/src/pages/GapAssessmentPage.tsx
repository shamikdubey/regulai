import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Plus, Loader2, Copy, Check, RotateCcw } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useJobPoller } from "@/hooks/useJobPoller";
import JobProgress from "@/components/features/JobProgress";
import { JURISDICTIONS, cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type GapItem = {
  jurisdiction: string;
  gap: string;
  requirement: string;
  risk_level: string;
  estimated_timeline: string;
  action_required: string;
};

type GapResult = {
  product_name: string;
  overall_risk: string;
  gaps: GapItem[];
  summary: string;
  critical_path: string[];
  estimated_total_months: number;
  latency_ms?: number;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const RISK_COLORS: Record<string, string> = {
  HIGH: "#dc2626",
  MEDIUM: "#f59e0b",
  LOW: "#0d9488",
};

const PRODUCT_TYPES = ["food", "pharma", "device", "nutra", "ayurveda"];

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatReportAsText(result: GapResult): string {
  const lines: string[] = [
    `GAP ASSESSMENT REPORT`,
    `=====================`,
    `Product: ${result.product_name}`,
    `Overall Risk: ${result.overall_risk}`,
    `Estimated Time to Full Compliance: ~${result.estimated_total_months} months`,
    ``,
    `SUMMARY`,
    `-------`,
    result.summary,
    ``,
    `COMPLIANCE GAPS (${result.gaps.length})`,
    `-`.repeat(30),
  ];

  result.gaps.forEach((g, i) => {
    lines.push(
      ``,
      `${i + 1}. [${g.risk_level}] ${g.jurisdiction.toUpperCase()}`,
      `   Gap: ${g.gap}`,
      `   Requirement: ${g.requirement}`,
      `   Action: ${g.action_required}`,
      `   Timeline: ${g.estimated_timeline}`,
    );
  });

  if (result.critical_path.length > 0) {
    lines.push(``, `CRITICAL PATH`, `-------------`);
    result.critical_path.forEach((s, i) => lines.push(`${i + 1}. ${s}`));
  }

  return lines.join("\n");
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function GapAssessmentPage() {
  const [searchParams] = useSearchParams();
  const [productName, setProductName]           = useState(searchParams.get("product") ?? "");
  const [productType, setProductType]           = useState("nutra");
  const [description, setDescription]           = useState("");
  const [claims, setClaims]                     = useState("");
  const [approvalsInput, setApprovalsInput]     = useState("");   // raw comma-sep string
  const initJurisdiction = searchParams.get("jurisdiction");
  const [jurisdictions, setJurisdictions]       = useState<string[]>(
    initJurisdiction ? [initJurisdiction] : [],
  );
  const [jobId, setJobId]                       = useState<string | null>(null);
  const [submitting, setSubmitting]             = useState(false);
  const [syncResult, setSyncResult]             = useState<GapResult | null>(null);
  const [copied, setCopied]                     = useState(false);

  const job = useJobPoller<GapResult>(jobId);
  const result: GapResult | null = job.result || syncResult;

  const toggleJur = (v: string) =>
    setJurisdictions((p) =>
      p.includes(v) ? p.filter((x) => x !== v) : [...p, v],
    );

  // ── Submit ────────────────────────────────────────────────────────────────

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!productName.trim() || jurisdictions.length === 0) {
      toast.error("Fill in product name and select at least one jurisdiction");
      return;
    }
    setSubmitting(true);
    setSyncResult(null);
    setJobId(null);
    setCopied(false);

    // Parse comma-separated approvals
    const currentApprovals = approvalsInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const resp = await getApiClient().post("/gap-assessment", {
        product_name:          productName,
        product_description:   description,
        product_type:          productType,
        target_jurisdictions:  jurisdictions,
        current_approvals:     currentApprovals,
        intended_claims:       claims,
      });
      if (resp.data.job_id) {
        setJobId(resp.data.job_id);
      } else {
        setSyncResult(resp.data);
      }
    } catch {
      toast.error("Failed to start gap assessment");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Clear / new assessment ────────────────────────────────────────────────

  const handleNewAssessment = () => {
    setSyncResult(null);
    setJobId(null);
    setCopied(false);
    setProductName("");
    setDescription("");
    setClaims("");
    setApprovalsInput("");
    setJurisdictions([]);
  };

  // ── Copy report ───────────────────────────────────────────────────────────

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(formatReportAsText(result));
      setCopied(true);
      toast.success("Report copied to clipboard");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error("Clipboard write failed — try copying manually");
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#0f172a]">Gap Assessment</h1>
          <p className="text-xs text-[#94a3b8] mt-1">
            Identify compliance gaps and required actions across target markets
          </p>
        </div>

        {/* New Assessment button — only shown when results are visible */}
        {result && (
          <button
            onClick={handleNewAssessment}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-xs text-[#64748b] hover:text-[#0f172a] hover:border-[#cbd5e1] transition-all flex-shrink-0 shadow-sm"
          >
            <RotateCcw size={12} />
            New Assessment
          </button>
        )}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Product name *
            </label>
            <input
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              required
              placeholder="e.g. OmegaPlus Fish Oil Capsules"
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Product type *
            </label>
            <select
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] capitalize"
            >
              {PRODUCT_TYPES.map((t) => (
                <option key={t} value={t} className="capitalize">
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
            Product description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Describe composition, intended use, dosage form..."
            className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors resize-none"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Intended claims (optional)
            </label>
            <input
              value={claims}
              onChange={(e) => setClaims(e.target.value)}
              placeholder="e.g. supports heart health, omega-3 supplement"
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Current approvals (optional)
            </label>
            <input
              value={approvalsInput}
              onChange={(e) => setApprovalsInput(e.target.value)}
              placeholder="e.g. US, EU, India (comma-separated)"
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-2 uppercase tracking-wider">
            Target jurisdictions * ({jurisdictions.length} selected)
          </label>
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto p-2 bg-[#f8fafc] border border-[#e2e8f0] rounded-xl">
            {JURISDICTIONS.map((j) => (
              <button
                type="button"
                key={j.value}
                onClick={() => toggleJur(j.value)}
                className={cn(
                  "flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs transition-all border",
                  jurisdictions.includes(j.value)
                    ? "bg-[#eff6ff] border-[#bfdbfe] text-[#2563eb]"
                    : "border-[#e2e8f0] text-[#94a3b8] hover:border-[#cbd5e1] hover:text-[#64748b]",
                )}
              >
                <span>{j.flag}</span>
                <span>{j.label}</span>
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting || job.isRunning}
          className={cn(
            "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
            submitting || job.isRunning
              ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
              : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
          )}
        >
          {submitting || job.isRunning ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Running…
            </>
          ) : (
            <>
              <TrendingUp size={14} />
              Run Gap Assessment
            </>
          )}
        </button>
      </form>

      <JobProgress
        job={job}
        title="Running gap assessment…"
        estimatedSeconds={90}
      />

      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4 mt-4"
          >
            {/* Summary */}
            <div className="bg-white border border-[#e2e8f0] rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-3 gap-3">
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-[#0f172a]">
                    {result.product_name}
                  </h2>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Copy report button */}
                  <button
                    onClick={handleCopy}
                    className={cn(
                      "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border transition-all",
                      copied
                        ? "bg-[#eff6ff] border-[#bfdbfe] text-[#2563eb]"
                        : "bg-white border-[#e2e8f0] text-[#94a3b8] hover:text-[#0f172a] hover:border-[#cbd5e1]",
                    )}
                  >
                    {copied ? (
                      <><Check size={11} />Copied</>
                    ) : (
                      <><Copy size={11} />Copy Report</>
                    )}
                  </button>
                  <span
                    className="text-xs font-bold px-3 py-1 rounded-full"
                    style={{
                      background: `${RISK_COLORS[result.overall_risk]}15`,
                      color: RISK_COLORS[result.overall_risk],
                    }}
                  >
                    {result.overall_risk} RISK
                  </span>
                </div>
              </div>

              <p className="text-sm text-[#64748b] leading-relaxed">
                {result.summary}
              </p>

              <div className="flex gap-4 mt-3 text-[11px] text-[#94a3b8] font-mono">
                <span>{result.gaps.length} gaps identified</span>
                <span>~{result.estimated_total_months} months to full compliance</span>
                {result.latency_ms && <span>{result.latency_ms}ms</span>}
              </div>
            </div>

            {/* Gaps */}
            {result.gaps.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-[#0f172a] uppercase tracking-wider">
                  Compliance gaps
                </h3>
                {result.gaps.map((g, i) => (
                  <div
                    key={i}
                    className="bg-white border border-[#e2e8f0] rounded-xl p-4 shadow-sm"
                    style={{
                      borderLeftWidth: 3,
                      borderLeftColor: RISK_COLORS[g.risk_level],
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-[#0f172a]">
                        {g.jurisdiction.toUpperCase()}
                      </span>
                      <span
                        className="text-[10px] font-bold"
                        style={{ color: RISK_COLORS[g.risk_level] }}
                      >
                        {g.risk_level}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-[#0f172a] mb-1">
                      {g.gap}
                    </p>
                    <p className="text-xs text-[#64748b] mb-2">
                      {g.requirement}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-[#94a3b8]">
                      <span>→ {g.action_required}</span>
                      <span className="font-mono">{g.estimated_timeline}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Critical path */}
            {result.critical_path.length > 0 && (
              <div className="bg-white border border-[#e2e8f0] rounded-2xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-[#0f172a] uppercase tracking-wider mb-3">
                  Critical path
                </h3>
                {result.critical_path.map((s, i) => (
                  <div key={i} className="flex items-start gap-3 mb-2">
                    <span className="w-5 h-5 rounded-full bg-[#eff6ff] text-[#2563eb] text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-xs text-[#64748b]">{s}</p>
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
