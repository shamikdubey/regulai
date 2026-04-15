import { useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { TrendingUp, Loader2, Copy, Check, RotateCcw, ArrowRight } from "lucide-react";
import TrustBadge, { confidenceToTrust } from "@/components/ui/TrustBadge";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useJobPoller } from "@/hooks/useJobPoller";
import JobProgress from "@/components/features/JobProgress";
import { JURISDICTIONS, cn } from "@/lib/utils";
import SearchableMultiSelect from "@/components/ui/SearchableMultiSelect";

// ── Types ─────────────────────────────────────────────────────────────────────

type GapItem = {
  jurisdiction: string;
  gap: string;
  requirement: string;
  risk_level: string;
  estimated_timeline: string;
  action_required: string;
  data_confidence?: string;
  registration_status?: string;
  source_url?: string | null;
  verification_url?: string;
  key_question?: string;
  risk_reason?: string;
  cost_range_usd?: string;
  required_documents?: string[];
};

type GapResult = {
  product_name: string;
  overall_risk: string;
  gaps: GapItem[];
  summary: string;
  critical_path: string[];
  estimated_total_months: number;
  latency_ms?: number;
  already_marketed_in?: string[];
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
  const [currentApprovals, setCurrentApprovals] = useState<string[]>([]);
  const initJurisdiction = searchParams.get("jurisdiction");
  // Store labels (e.g. "India") — convert to values on submit
  const initLabel = initJurisdiction
    ? (JURISDICTIONS.find((j) => j.value === initJurisdiction)?.label ?? initJurisdiction)
    : null;
  const [jurisdictions, setJurisdictions]       = useState<string[]>(
    initLabel ? [initLabel] : [],
  );
  const [jobId, setJobId]                       = useState<string | null>(null);
  const [submitting, setSubmitting]             = useState(false);
  const [syncResult, setSyncResult]             = useState<GapResult | null>(null);
  const [copied, setCopied]                     = useState(false);

  const job = useJobPoller<GapResult>(jobId);
  const result: GapResult | null = job.result || syncResult;

  // Convert label → value for API submission
  const labelToValue = (label: string): string =>
    JURISDICTIONS.find((j) => j.label === label)?.value ?? label.toLowerCase();

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

    // Convert labels to API values
    const jurisdictionValues = jurisdictions.map(labelToValue);
    // currentApprovals already stored as labels — convert to values for API
    const approvalValues = currentApprovals.map(labelToValue);

    try {
      const resp = await getApiClient().post("/gap-assessment", {
        product_name:          productName,
        product_description:   description,
        product_type:          productType,
        target_jurisdictions:  jurisdictionValues,
        current_approvals:     approvalValues,
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
    setCurrentApprovals([]);
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
          <h1 className="text-xl font-bold text-[#111827]">Gap Assessment</h1>
          <p className="text-xs text-[#374151] mt-1">
            Identify compliance gaps and required actions across target markets
          </p>
        </div>

        {/* New Assessment button — only shown when results are visible */}
        {result && (
          <button
            onClick={handleNewAssessment}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-xs text-[#6b7280] hover:text-[#111827] hover:border-[#cbd5e1] transition-all flex-shrink-0 shadow-sm"
          >
            <RotateCcw size={12} />
            New Assessment
          </button>
        )}
      </div>

      {/* Recommended workflow */}
      <div className="mb-5 p-3.5 bg-[#f7faf9] border border-[#e2ede9] rounded-xl">
        <p className="text-[9px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2.5">Recommended workflow</p>
        <div className="flex items-center gap-1.5 flex-wrap">
          {[
            { label: "Gap Assessment", to: "/gap-assessment" },
            { label: "Filing Wizard", to: "/filing-wizard" },
            { label: "Document Editor", to: "/document-editor" },
            { label: "Compliance Review", to: "/compliance-review" },
          ].map((step, i, arr) => (
            <div key={step.to} className="flex items-center gap-1.5">
              <Link
                to={step.to}
                className={cn(
                  "text-xs px-2 py-1 rounded-lg font-semibold transition-colors",
                  step.to === "/gap-assessment"
                    ? "bg-[#ecfdf5] border border-[#a7f3d0] text-[#047857]"
                    : "text-[#6b7280] hover:text-[#047857]",
                )}
              >
                {step.label}
              </Link>
              {i < arr.length - 1 && (
                <ArrowRight size={11} className="text-[#cbd5e1] flex-shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4 mb-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
              Product name *
            </label>
            <input
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              required
              placeholder="e.g. OmegaPlus Fish Oil Capsules"
              className="w-full px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors"
            />
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
              Product type *
            </label>
            <select
              value={productType}
              onChange={(e) => setProductType(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] capitalize"
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
          <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
            Product description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Describe your product in detail — include intended use, how it works, materials, whether implantable, duration of use. More detail = more accurate gap analysis."
            className="w-full px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors resize-none"
          />
          <p className="text-[10px] text-[#9ca3af] mt-1">
            The AI uses this to classify your product and search regulatory databases accurately
          </p>
        </div>

        <div>
          <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
            Intended claims (optional)
          </label>
          <input
            value={claims}
            onChange={(e) => setClaims(e.target.value)}
            placeholder="e.g. supports heart health, omega-3 supplement"
            className="w-full px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors"
          />
        </div>

        <div className="bg-[#f0fdf4] border border-[#bbf7d0] rounded-xl p-4">
          <label className="block text-[10px] font-mono text-[#047857] mb-1 uppercase tracking-wider font-bold">
            Countries where this product is ALREADY APPROVED ✓
          </label>
          <p className="text-[11px] text-[#6b7280] mb-2">
            Select countries where you have confirmed regulatory approval. This focuses gap analysis on new markets only.
          </p>
          <SearchableMultiSelect
            options={JURISDICTIONS.map((j) => j.label)}
            selected={currentApprovals}
            onChange={setCurrentApprovals}
            placeholder="Search approved countries…"
          />
          {currentApprovals.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {currentApprovals.map((c) => (
                <span key={c} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#dcfce7] text-[#047857] text-[11px] font-semibold rounded-full border border-[#bbf7d0]">
                  ✓ {c}
                </span>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="block text-[10px] font-mono text-[#9ca3af] mb-2 uppercase tracking-wider">
            Target jurisdictions * ({jurisdictions.length} selected)
          </label>
          <SearchableMultiSelect
            options={JURISDICTIONS.map((j) => j.label)}
            selected={jurisdictions}
            onChange={setJurisdictions}
            placeholder="Search jurisdictions…"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || job.isRunning}
          className={cn(
            "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
            submitting || job.isRunning
              ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
              : "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]",
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
            {/* Disclaimer banner */}
            <div className="flex items-start gap-2.5 p-3.5 bg-[#fffbeb] border border-[#fde68a] rounded-xl">
              <span className="text-sm flex-shrink-0">⚠️</span>
              <p className="text-[11px] text-[#92400e] leading-relaxed">
                Gap analysis is AI-generated and web-searched. Registration status shown is based on publicly available data as of the search date. Always verify with the relevant regulatory authority before making filing decisions.
              </p>
            </div>

            {/* Summary */}
            <div className="bg-white border border-[#e2ede9] rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-3 gap-3">
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-[#111827]">
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
                        ? "bg-[#ecfdf5] border-[#a7f3d0] text-[#047857]"
                        : "bg-white border-[#e2ede9] text-[#9ca3af] hover:text-[#111827] hover:border-[#cbd5e1]",
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

              <p className="text-sm text-[#6b7280] leading-relaxed">
                {result.summary}
              </p>

              {result.already_marketed_in && result.already_marketed_in.length > 0 && (
                <div className="mt-3 p-2.5 bg-[#f0fdf4] border border-[#bbf7d0] rounded-lg">
                  <p className="text-[10px] font-mono text-[#047857] font-bold mb-1">LIKELY ALREADY MARKETED IN</p>
                  <p className="text-xs text-[#047857]">{result.already_marketed_in.join(", ")}</p>
                </div>
              )}

              <div className="flex gap-4 mt-3 text-[11px] text-[#374151] font-mono">
                <span>{result.gaps.length} gaps identified</span>
                <span>~{result.estimated_total_months} months to full compliance</span>
                {result.latency_ms && <span>{result.latency_ms}ms</span>}
              </div>
            </div>

            {/* Gaps */}
            {result.gaps.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-bold text-[#111827] uppercase tracking-wider">
                  Compliance gaps
                </h3>
                {result.gaps.map((g, i) => (
                  <div
                    key={i}
                    className="bg-white border border-[#e2ede9] rounded-xl p-4 shadow-sm"
                    style={{
                      borderLeftWidth: 3,
                      borderLeftColor: RISK_COLORS[g.risk_level],
                    }}
                  >
                    {/* Registration status badge */}
                    {g.registration_status && (
                      <div className="flex items-center gap-2 mb-2.5 flex-wrap">
                        {g.registration_status === "USER_CONFIRMED_APPROVED" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#dcfce7] text-[#047857] text-[10px] font-bold rounded-full border border-[#bbf7d0]">
                            🟢 You confirmed: Approved
                          </span>
                        )}
                        {g.registration_status === "FOUND_IN_DATABASE" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded-full border border-blue-200">
                            🔵 Found in regulatory database
                          </span>
                        )}
                        {g.registration_status === "NOT_FOUND" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 text-[10px] font-bold rounded-full border border-red-200">
                            🔴 Not found in database
                          </span>
                        )}
                        {g.registration_status === "UNKNOWN" && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-50 text-gray-500 text-[10px] font-bold rounded-full border border-gray-200">
                            ⚪ Status unknown
                          </span>
                        )}
                        {g.source_url && (
                          <a
                            href={g.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-blue-600 hover:underline"
                          >
                            View registration →
                          </a>
                        )}
                      </div>
                    )}

                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-mono font-bold text-[#111827]">
                        {g.jurisdiction.toUpperCase()}
                      </span>
                      <div className="flex items-center gap-2">
                        {g.data_confidence && (
                          <TrustBadge {...confidenceToTrust(g.data_confidence)} />
                        )}
                        <span
                          className="text-[10px] font-bold"
                          style={{ color: RISK_COLORS[g.risk_level] }}
                        >
                          {g.risk_level}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs font-semibold text-[#111827] mb-1">
                      {g.gap}
                    </p>
                    <p className="text-xs text-[#6b7280] mb-2">
                      {g.requirement}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-[#374151]">
                      <span>→ {g.action_required}</span>
                      <span className="font-mono">{g.estimated_timeline}</span>
                    </div>

                    {/* Verify at official source */}
                    {g.verification_url && (
                      <div className="mt-2.5 pt-2.5 border-t border-[#f0f4f2]">
                        <a
                          href={g.verification_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[10px] text-[#047857] hover:underline font-medium"
                        >
                          🔗 Verify at {g.jurisdiction} regulatory database →
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Critical path */}
            {result.critical_path.length > 0 && (
              <div className="bg-white border border-[#e2ede9] rounded-2xl p-5 shadow-sm">
                <h3 className="text-xs font-bold text-[#111827] uppercase tracking-wider mb-3">
                  Critical path
                </h3>
                {result.critical_path.map((s, i) => (
                  <div key={i} className="flex items-start gap-3 mb-2">
                    <span className="w-5 h-5 rounded-full bg-[#ecfdf5] text-[#047857] text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    <p className="text-xs text-[#6b7280]">{s}</p>
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
