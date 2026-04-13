import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useDropzone } from "react-dropzone";
import { useQuery } from "@tanstack/react-query";
import {
  Upload, FileText, X, Loader2, CheckCircle2,
  AlertTriangle, XCircle, RefreshCw, ChevronDown, ChevronUp,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type ComplianceStatus = "COMPLIANT" | "PARTIALLY_COMPLIANT" | "NON_COMPLIANT";
type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

type Finding = {
  id: string;
  title: string;
  description: string;
  severity: Severity;
  recommendation: string;
  regulation_reference?: string;
};

type ReviewResult = {
  id: string;
  filename: string;
  overall_status: ComplianceStatus;
  score: number;
  summary: string;
  findings: Finding[];
  jurisdiction: string;
  domain: string;
  reviewed_at: string;
};

type ReviewListItem = {
  id: string;
  filename: string;
  overall_status: ComplianceStatus;
  score: number;
  jurisdiction: string;
  domain: string;
  reviewed_at: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const JURISDICTIONS = [
  "US", "EU", "UK", "India", "Japan", "China", "Singapore",
  "Malaysia", "Thailand", "Vietnam", "Indonesia", "South Korea",
  "Australia", "Canada",
];

const DOMAINS = [
  { value: "MEDICAL_DEVICE", label: "Medical Device" },
  { value: "FOOD", label: "Food Product" },
  { value: "PHARMA", label: "Pharmaceutical" },
  { value: "NUTRA", label: "Nutraceutical" },
];

const STATUS_CONFIG: Record<
  ComplianceStatus,
  { label: string; color: string; icon: typeof CheckCircle2 }
> = {
  COMPLIANT: { label: "Compliant", color: "#0d9488", icon: CheckCircle2 },
  PARTIALLY_COMPLIANT: {
    label: "Partially Compliant",
    color: "#f59e0b",
    icon: AlertTriangle,
  },
  NON_COMPLIANT: { label: "Non-Compliant", color: "#dc2626", icon: XCircle },
};

const SEVERITY_COLORS: Record<Severity, string> = {
  CRITICAL: "#dc2626",
  HIGH: "#f59e0b",
  MEDIUM: "#0f172a",
  LOW: "#94a3b8",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function ComplianceReviewPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [jurisdiction, setJurisdiction] = useState("US");
  const [domain, setDomain] = useState("MEDICAL_DEVICE");
  const [isReviewing, setIsReviewing] = useState(false);
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null);

  // ── Dropzone ───────────────────────────────────────────────────────────────

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) {
      setSelectedFile(accepted[0]);
      setReviewResult(null);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/msword": [".doc"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        [".docx"],
      "text/plain": [".txt"],
      "text/rtf": [".rtf"],
    },
    maxSize: 20 * 1024 * 1024, // 20 MB
    maxFiles: 1,
    onDropRejected: (rejections) => {
      const reason = rejections[0]?.errors[0]?.code;
      if (reason === "file-too-large") {
        toast.error("File too large — max 20 MB");
      } else if (reason === "file-invalid-type") {
        toast.error("Unsupported file type — use PDF, DOC, DOCX, TXT, or RTF");
      } else {
        toast.error("File rejected");
      }
    },
  });

  // ── Review history ─────────────────────────────────────────────────────────

  const historyQ = useQuery({
    queryKey: ["compliance-reviews"],
    queryFn: () =>
      getApiClient()
        .get<ReviewListItem[]>("/compliance-review/reviews")
        .then((r) => r.data),
    enabled: showHistory,
  });

  // ── Submit review ──────────────────────────────────────────────────────────

  const handleReview = async () => {
    if (!selectedFile) return;
    setIsReviewing(true);
    setReviewResult(null);
    try {
      const fd = new FormData();
      fd.append("file", selectedFile);
      fd.append("jurisdiction", jurisdiction);
      fd.append("domain", domain);

      const { data } = await getApiClient().post<ReviewResult>(
        "/compliance-review/reviews",
        fd,
        { headers: { "Content-Type": "multipart/form-data" } },
      );

      setReviewResult(data);
      toast.success("Review complete");
    } catch {
      toast.error("Compliance review failed");
    } finally {
      setIsReviewing(false);
    }
  };

  const clearFile = () => {
    setSelectedFile(null);
    setReviewResult(null);
  };

  // ── Helpers ────────────────────────────────────────────────────────────────

  const statusCfg = reviewResult
    ? STATUS_CONFIG[reviewResult.overall_status]
    : null;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#0f172a]">
            Compliance Review
          </h1>
          <p className="text-xs text-[#94a3b8] mt-1">
            Upload a document to assess regulatory compliance
          </p>
        </div>
        <button
          onClick={() => setShowHistory((p) => !p)}
          className="flex items-center gap-1.5 px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-xs text-[#64748b] hover:text-[#0f172a] hover:border-[#cbd5e1] transition-all flex-shrink-0 shadow-sm"
        >
          <FileText size={13} />
          History
          {showHistory ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
        </button>
      </div>

      {/* Review history panel */}
      <AnimatePresence>
        {showHistory && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-5 bg-white border border-[#e2e8f0] rounded-2xl p-4 shadow-sm"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider">
                Past reviews
              </span>
              <button
                onClick={() => historyQ.refetch()}
                className="text-[#94a3b8] hover:text-[#0f172a] transition-colors"
              >
                <RefreshCw size={12} />
              </button>
            </div>

            {historyQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-[#94a3b8]">
                <Loader2 size={13} className="animate-spin" />
                <span className="text-xs">Loading…</span>
              </div>
            ) : historyQ.isError ? (
              <p className="text-xs text-[#dc2626] py-4 text-center">
                Failed to load history
              </p>
            ) : (historyQ.data ?? []).length === 0 ? (
              <p className="text-xs text-[#94a3b8] py-4 text-center">
                No reviews yet
              </p>
            ) : (
              <div className="space-y-1.5 max-h-56 overflow-y-auto">
                {(historyQ.data ?? []).map((r) => {
                  const cfg = STATUS_CONFIG[r.overall_status];
                  return (
                    <div
                      key={r.id}
                      className="flex items-center justify-between p-2.5 bg-[#f8fafc] border border-[#e2e8f0] rounded-xl"
                    >
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-[#0f172a] truncate">
                          {r.filename}
                        </p>
                        <p className="text-[10px] text-[#94a3b8] font-mono mt-0.5">
                          {r.jurisdiction} · {r.domain.replace(/_/g, " ")} ·{" "}
                          {new Date(r.reviewed_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span
                        className="ml-3 text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0"
                        style={{
                          background: `${cfg.color}15`,
                          color: cfg.color,
                        }}
                      >
                        {r.score}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload + config form */}
      <div className="space-y-4 mb-6">
        {/* Dropzone */}
        <div>
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-2 uppercase tracking-wider">
            Document *
          </label>
          {selectedFile ? (
            <div className="flex items-center gap-3 px-4 py-3 bg-white border border-[rgba(37,99,235,0.3)] rounded-xl shadow-sm">
              <FileText size={16} className="text-[#2563eb] flex-shrink-0" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-[#0f172a] truncate">
                  {selectedFile.name}
                </p>
                <p className="text-[10px] text-[#94a3b8] font-mono mt-0.5">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <button
                onClick={clearFile}
                className="text-[#94a3b8] hover:text-[#dc2626] transition-colors flex-shrink-0"
              >
                <X size={14} />
              </button>
            </div>
          ) : (
            <div
              {...getRootProps()}
              className={cn(
                "flex flex-col items-center justify-center gap-3 py-10 border-2 border-dashed rounded-xl cursor-pointer transition-all",
                isDragActive
                  ? "border-[#2563eb] bg-[#eff6ff]"
                  : "border-[#e2e8f0] hover:border-[#cbd5e1] bg-white",
              )}
            >
              <input {...getInputProps()} />
              <Upload
                size={28}
                className={cn(
                  "transition-colors",
                  isDragActive ? "text-[#2563eb]" : "text-[#cbd5e1]",
                )}
              />
              <div className="text-center">
                <p className="text-sm font-medium text-[#64748b]">
                  {isDragActive
                    ? "Drop to upload"
                    : "Drop document here or click to browse"}
                </p>
                <p className="text-[10px] text-[#94a3b8] mt-1">
                  PDF, DOC, DOCX, TXT, RTF — max 20 MB
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Jurisdiction + domain */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Jurisdiction
            </label>
            <select
              value={jurisdiction}
              onChange={(e) => setJurisdiction(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
            >
              {JURISDICTIONS.map((j) => (
                <option key={j} value={j}>
                  {j}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
              Regulatory domain
            </label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
            >
              {DOMAINS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Submit */}
        <button
          onClick={handleReview}
          disabled={!selectedFile || isReviewing}
          className={cn(
            "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
            !selectedFile || isReviewing
              ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
              : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
          )}
        >
          {isReviewing ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Reviewing…
            </>
          ) : (
            <>
              <CheckCircle2 size={14} />
              Run Compliance Review
            </>
          )}
        </button>
      </div>

      {/* Results */}
      <AnimatePresence>
        {reviewResult && statusCfg && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Overall status card */}
            <div className="bg-white border border-[#e2e8f0] rounded-2xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h2 className="text-base font-bold text-[#0f172a]">
                    {reviewResult.filename}
                  </h2>
                  <p className="text-[10px] text-[#94a3b8] font-mono mt-0.5">
                    {reviewResult.jurisdiction} ·{" "}
                    {reviewResult.domain.replace(/_/g, " ")} ·{" "}
                    {new Date(reviewResult.reviewed_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span
                    className="text-xs font-bold px-3 py-1 rounded-full"
                    style={{
                      background: `${statusCfg.color}15`,
                      color: statusCfg.color,
                    }}
                  >
                    {statusCfg.label}
                  </span>
                </div>
              </div>

              {/* Score bar */}
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] text-[#94a3b8]">
                    Compliance score
                  </span>
                  <span
                    className="text-sm font-bold font-mono"
                    style={{ color: statusCfg.color }}
                  >
                    {reviewResult.score}%
                  </span>
                </div>
                <div className="h-2 bg-[#e2e8f0] rounded-full overflow-hidden">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ background: statusCfg.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${reviewResult.score}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                </div>
              </div>

              <p className="text-sm text-[#64748b] leading-relaxed">
                {reviewResult.summary}
              </p>

              <p className="text-[10px] text-[#94a3b8] font-mono mt-2">
                {reviewResult.findings.length} finding
                {reviewResult.findings.length !== 1 ? "s" : ""}
              </p>
            </div>

            {/* Findings */}
            {reviewResult.findings.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-[10px] font-bold text-[#0f172a] uppercase tracking-wider">
                  Findings
                </h3>
                {reviewResult.findings.map((f) => (
                  <div
                    key={f.id}
                    className="bg-white border border-[#e2e8f0] rounded-xl overflow-hidden shadow-sm"
                    style={{
                      borderLeftWidth: 3,
                      borderLeftColor: SEVERITY_COLORS[f.severity],
                    }}
                  >
                    <button
                      className="w-full flex items-center justify-between p-4 text-left"
                      onClick={() =>
                        setExpandedFinding((p) =>
                          p === f.id ? null : f.id,
                        )
                      }
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span
                          className="text-[9px] font-bold flex-shrink-0"
                          style={{ color: SEVERITY_COLORS[f.severity] }}
                        >
                          {f.severity}
                        </span>
                        <span className="text-xs font-semibold text-[#0f172a] truncate">
                          {f.title}
                        </span>
                      </div>
                      {expandedFinding === f.id ? (
                        <ChevronUp
                          size={13}
                          className="text-[#94a3b8] flex-shrink-0 ml-2"
                        />
                      ) : (
                        <ChevronDown
                          size={13}
                          className="text-[#94a3b8] flex-shrink-0 ml-2"
                        />
                      )}
                    </button>

                    <AnimatePresence>
                      {expandedFinding === f.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-4 space-y-2 border-t border-[#e2e8f0] pt-3 bg-[#f8fafc]">
                            <p className="text-xs text-[#64748b]">
                              {f.description}
                            </p>
                            <div className="flex items-start gap-2">
                              <span className="text-[10px] font-bold text-[#2563eb] flex-shrink-0 mt-0.5">
                                Recommendation:
                              </span>
                              <p className="text-xs text-[#64748b]">
                                {f.recommendation}
                              </p>
                            </div>
                            {f.regulation_reference && (
                              <p className="text-[10px] text-[#94a3b8] font-mono">
                                Ref: {f.regulation_reference}
                              </p>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
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
