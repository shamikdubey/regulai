import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen, Plus, Loader2, Download, Star,
  X, PenLine, AlertTriangle, RefreshCw,
  Apple, Activity, Pill, Leaf, Sprout, Filter,
} from "lucide-react";
import toast from "react-hot-toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import SearchableMultiSelect from "@/components/ui/SearchableMultiSelect";
import TrustBadge, { trustLevelFromScore } from "@/components/ui/TrustBadge";

// ── Types ─────────────────────────────────────────────────────────────────────

type Template = {
  id: string;
  title: string;
  slug: string;
  country: string;
  domain: string;
  document_type: string;
  regulation_reference?: string;
  trust_score: number;
  trust_level: string;
  avg_user_rating: number;
  feedback_count: number;
  is_ai_generated: boolean;
  content_html?: string;
  confidence_note?: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const DOMAINS = [
  { value: "FOOD",           label: "Food & Food Additives",      icon: Apple,    color: "#f59e0b" },
  { value: "MEDICAL_DEVICE", label: "Medical Devices",            icon: Activity, color: "#047857" },
  { value: "PHARMA",         label: "Pharmaceuticals/APIs",       icon: Pill,     color: "#7c3aed" },
  { value: "NUTRACEUTICAL",  label: "Nutraceuticals/Supplements", icon: Leaf,     color: "#0d9488" },
  { value: "TRADITIONAL",    label: "Ayurveda/Traditional",       icon: Sprout,   color: "#92400e" },
];

const DOC_TYPES = [
  { value: "CHECKLIST",           label: "Checklist" },
  { value: "COVER_LETTER",        label: "Cover Letter" },
  { value: "TECHNICAL_FILE",      label: "Technical File" },
  { value: "REGULATORY_SUMMARY",  label: "Regulatory Summary" },
  { value: "RISK_ASSESSMENT",     label: "Risk Assessment" },
];

const COUNTRIES = [
  "India", "USA", "UK", "EU", "China", "Japan",
  "Brazil", "Australia", "Canada", "Singapore",
  "South Korea", "Indonesia", "Thailand", "Malaysia", "Philippines",
  "UAE", "Saudi Arabia", "Turkey", "Israel", "South Africa",
  "Nigeria", "Kenya", "Ghana", "New Zealand", "Mexico",
  "Argentina", "Colombia", "Chile", "Peru", "Switzerland",
  "Norway", "Russia", "Poland", "Kazakhstan", "Vietnam",
  "Bangladesh", "Pakistan", "Sri Lanka", "Myanmar", "Ethiopia",
  "Taiwan", "Hong Kong", "Egypt", "Algeria", "Morocco",
  "Tanzania", "Uganda", "Cameroon", "Ivory Coast", "Senegal",
];

const COUNTRY_FLAGS: Record<string, string> = {
  India: "🇮🇳", USA: "🇺🇸", UK: "🇬🇧", EU: "🇪🇺", China: "🇨🇳",
  Japan: "🇯🇵", Brazil: "🇧🇷", Australia: "🇦🇺", Canada: "🇨🇦",
  Singapore: "🇸🇬", "South Korea": "🇰🇷", Indonesia: "🇮🇩",
  Thailand: "🇹🇭", Malaysia: "🇲🇾", Philippines: "🇵🇭",
  UAE: "🇦🇪", "Saudi Arabia": "🇸🇦", Turkey: "🇹🇷", Israel: "🇮🇱",
  "South Africa": "🇿🇦", Nigeria: "🇳🇬", Kenya: "🇰🇪", Ghana: "🇬🇭",
  "New Zealand": "🇳🇿", Mexico: "🇲🇽", Argentina: "🇦🇷",
  Colombia: "🇨🇴", Chile: "🇨🇱", Peru: "🇵🇪", Switzerland: "🇨🇭",
  Norway: "🇳🇴", Russia: "🇷🇺", Poland: "🇵🇱", Kazakhstan: "🇰🇿",
  Vietnam: "🇻🇳", Bangladesh: "🇧🇩", Pakistan: "🇵🇰", "Sri Lanka": "🇱🇰",
  Myanmar: "🇲🇲", Ethiopia: "🇪🇹", Taiwan: "🇹🇼", "Hong Kong": "🇭🇰",
  Egypt: "🇪🇬", Algeria: "🇩🇿", Morocco: "🇲🇦", Tanzania: "🇹🇿",
  Uganda: "🇺🇬", Cameroon: "🇨🇲", "Ivory Coast": "🇨🇮", Senegal: "🇸🇳",
};

const DOMAIN_COLORS: Record<string, string> = {
  FOOD: "#f59e0b", MEDICAL_DEVICE: "#047857", PHARMA: "#7c3aed",
  NUTRACEUTICAL: "#0d9488", TRADITIONAL: "#92400e",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function domainLabel(value: string) {
  return DOMAINS.find((d) => d.value === value)?.label ?? value.replace(/_/g, " ");
}

function docTypeLabel(value: string) {
  return DOC_TYPES.find((d) => d.value === value)?.label ?? value.replace(/_/g, " ");
}

function flagFor(country: string) {
  return COUNTRY_FLAGS[country] ?? "🌍";
}

function StarRow({ rating, max = 5 }: { rating: number; max?: number }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {Array.from({ length: max }).map((_, i) => (
        <Star
          key={i}
          size={10}
          className={i < Math.round(rating) ? "text-[#f59e0b]" : "text-[#e2ede9]"}
          fill={i < Math.round(rating) ? "#f59e0b" : "#e2ede9"}
        />
      ))}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function TemplateLibraryPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  // Filters
  const [filterSearch,  setFilterSearch]  = useState("");
  const [filterCountry, setFilterCountry] = useState("");
  const [filterDomain,  setFilterDomain]  = useState("");
  const [filterDocType, setFilterDocType] = useState("");

  // Modals
  const [showGenModal,      setShowGenModal]      = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState<{ id: string; title: string } | null>(null);
  const [newTemplate,       setNewTemplate]       = useState<Template | null>(null);

  // Generate form
  const [genCountry,     setGenCountry]     = useState<string[]>([]);
  const [genDomain,      setGenDomain]      = useState<string | null>(null);
  const [genDocType,     setGenDocType]     = useState("");
  const [genProductName, setGenProductName] = useState("");

  // Feedback form
  const [fbRating,    setFbRating]    = useState(0);
  const [fbAccurate,  setFbAccurate]  = useState<boolean | null>(null);
  const [fbText,      setFbText]      = useState("");
  const [hoverStar,   setHoverStar]   = useState(0);

  // ── Queries ────────────────────────────────────────────────────────────────

  const listParams: Record<string, string> = {};
  if (filterSearch)  listParams.search        = filterSearch;
  if (filterCountry) listParams.country       = filterCountry;
  if (filterDomain)  listParams.domain        = filterDomain;
  if (filterDocType) listParams.document_type = filterDocType;

  const templatesQ = useQuery({
    queryKey: ["template-library", listParams],
    queryFn: () => api.templateLibrary.list(listParams),
  });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const generateMut = useMutation({
    mutationFn: () =>
      api.templateLibrary.generate({
        country: genCountry[0] ?? "",
        domain: genDomain ?? "",
        document_type: genDocType,
        ...(genProductName.trim() && { product_name: genProductName.trim() }),
      }),
    onSuccess: (data) => {
      setNewTemplate(data as Template);
      setShowGenModal(false);
      toast.success("Template generated");
      qc.invalidateQueries({ queryKey: ["template-library"] });
      // Reset form
      setGenCountry([]);
      setGenDomain(null);
      setGenDocType("");
      setGenProductName("");
    },
    onError: () => toast.error("Generation failed — try again"),
  });

  const feedbackMut = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      api.templateLibrary.feedback(id, {
        rating: fbRating,
        is_accurate: fbAccurate,
        ...(fbText.trim() && { feedback_text: fbText.trim() }),
      }),
    onSuccess: () => {
      toast.success("Thank you for your feedback!");
      setShowFeedbackModal(null);
      setFbRating(0);
      setFbAccurate(null);
      setFbText("");
      qc.invalidateQueries({ queryKey: ["template-library"] });
    },
    onError: () => toast.error("Failed to submit feedback"),
  });

  // ── Download ───────────────────────────────────────────────────────────────

  const handleDownload = async (t: Template) => {
    try {
      const blob = await api.templateLibrary.download(t.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${t.country}-${t.domain}-${t.document_type}.docx`.toLowerCase().replace(/\s+/g, "-");
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Download failed");
    }
  };

  // ── Open in Editor ─────────────────────────────────────────────────────────

  const openInEditor = (t: Template) => {
    navigate("/document-editor", { state: { templateContent: t.content_html, templateTitle: t.title } });
  };

  // ── Template card ──────────────────────────────────────────────────────────

  const TemplateCard = ({ t, isNew }: { t: Template; isNew?: boolean }) => {
    const domColor = DOMAIN_COLORS[t.domain] ?? "#6b7280";
    const trustLevel = t.trust_level || trustLevelFromScore(t.trust_score);

    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "bg-white border rounded-2xl p-4 shadow-sm flex flex-col gap-3",
          isNew ? "border-[#f59e0b] ring-1 ring-[#f59e0b]" : "border-[#e2ede9]",
        )}
      >
        {/* AI-generated warning */}
        {(isNew || t.is_ai_generated) && (
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#fffbeb] border border-[#fde68a] rounded-lg">
            <AlertTriangle size={11} className="text-[#f59e0b] flex-shrink-0" />
            <span className="text-[10px] font-semibold text-[#b45309]">
              AI Generated — Review before use in official submissions
            </span>
          </div>
        )}

        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-base leading-none">{flagFor(t.country)}</span>
            <span className="text-[10px] font-mono text-[#6b7280]">{t.country}</span>
            <span
              className="text-[9px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: `${domColor}15`, color: domColor }}
            >
              {domainLabel(t.domain)}
            </span>
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-[#f7faf9] text-[#6b7280] border border-[#e2ede9]">
              {docTypeLabel(t.document_type)}
            </span>
          </div>
        </div>

        {/* Title */}
        <p className="text-sm font-bold text-[#111827] leading-snug">{t.title}</p>

        {/* Regulation reference */}
        {t.regulation_reference && (
          <p className="text-[10px] text-[#6b7280] font-mono leading-relaxed border-l-2 border-[#e2ede9] pl-2">
            {t.regulation_reference}
          </p>
        )}

        {/* Trust score bar */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <TrustBadge score={t.trust_score} level={trustLevel} showScore />
            <div className="flex items-center gap-1">
              <StarRow rating={Number(t.avg_user_rating) || 0} />
              {t.feedback_count > 0 && (
                <span className="text-[9px] text-[#9ca3af] font-mono">
                  ({t.feedback_count})
                </span>
              )}
            </div>
          </div>
          <div className="h-1 bg-[#e2ede9] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${t.trust_score}%`,
                background: t.trust_score >= 90 ? "#10b981"
                  : t.trust_score >= 75 ? "#3b82f6"
                  : t.trust_score >= 50 ? "#f59e0b"
                  : t.trust_score >= 25 ? "#ef4444"
                  : "#9ca3af",
              }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 pt-1 border-t border-[#f7faf9] flex-wrap">
          <button
            onClick={() => openInEditor(t)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#ecfdf5] text-[#047857] text-[10px] font-bold hover:bg-[#d1fae5] transition-colors"
          >
            <PenLine size={11} />
            Open in Editor
          </button>
          <button
            onClick={() => handleDownload(t)}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#f7faf9] border border-[#e2ede9] text-[#6b7280] text-[10px] font-bold hover:text-[#111827] hover:border-[#cbd5e1] transition-colors"
          >
            <Download size={11} />
            Download DOCX
          </button>
          <button
            onClick={() => setShowFeedbackModal({ id: t.id, title: t.title })}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-[#f7faf9] border border-[#e2ede9] text-[#6b7280] text-[10px] font-bold hover:text-[#111827] hover:border-[#cbd5e1] transition-colors"
          >
            <Star size={11} />
            Rate this
          </button>
        </div>
      </motion.div>
    );
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  const templates: Template[] = (templatesQ.data as Template[]) ?? [];

  return (
    <div className="p-6 max-w-6xl mx-auto">

      {/* Page header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-[#ecfdf5] border border-[#a7f3d0] rounded-xl flex items-center justify-center flex-shrink-0">
            <BookOpen size={18} className="text-[#047857]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-[#111827]">Template Library</h1>
            <p className="text-xs text-[#9ca3af] mt-0.5">
              Pre-built regulatory documents for 100+ countries. AI-generated, expert-verified.
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowGenModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#047857] text-white rounded-xl text-xs font-bold hover:bg-[#065f46] active:scale-[0.98] transition-all flex-shrink-0"
        >
          <Plus size={13} />
          Generate Template
        </button>
      </div>

      {/* Trust legend */}
      <div className="mb-5 flex items-center gap-4 flex-wrap px-4 py-2.5 bg-white border border-[#e2ede9] rounded-xl shadow-sm">
        <span className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider flex-shrink-0">Trust level:</span>
        {[
          { level: "VERIFIED",   score: 95, dot: "#10b981" },
          { level: "HIGH",       score: 80, dot: "#3b82f6" },
          { level: "MODERATE",   score: 60, dot: "#f59e0b" },
          { level: "LOW",        score: 30, dot: "#ef4444" },
          { level: "UNVERIFIED", score: 10, dot: "#9ca3af" },
        ].map((item) => (
          <TrustBadge key={item.level} score={item.score} level={item.level} />
        ))}
      </div>

      {/* Filters */}
      <div className="mb-5 flex items-center gap-2 flex-wrap">
        <div className="flex items-center gap-1.5 flex-1 min-w-48 bg-white border border-[#e2ede9] rounded-xl px-3 py-2 focus-within:border-[#047857] transition-colors">
          <Filter size={12} className="text-[#9ca3af] flex-shrink-0" />
          <input
            value={filterSearch}
            onChange={(e) => setFilterSearch(e.target.value)}
            placeholder="Search templates…"
            className="flex-1 text-xs outline-none text-[#111827] placeholder-[#9ca3af] bg-transparent"
          />
          {filterSearch && (
            <button onClick={() => setFilterSearch("")} className="text-[#9ca3af] hover:text-[#111827]">
              <X size={11} />
            </button>
          )}
        </div>

        <select
          value={filterCountry}
          onChange={(e) => setFilterCountry(e.target.value)}
          className="px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-xs text-[#111827] outline-none focus:border-[#047857] transition-colors"
        >
          <option value="">All countries</option>
          {COUNTRIES.map((c) => (
            <option key={c} value={c}>{flagFor(c)} {c}</option>
          ))}
        </select>

        <select
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          className="px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-xs text-[#111827] outline-none focus:border-[#047857] transition-colors"
        >
          <option value="">All domains</option>
          {DOMAINS.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>

        <select
          value={filterDocType}
          onChange={(e) => setFilterDocType(e.target.value)}
          className="px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-xs text-[#111827] outline-none focus:border-[#047857] transition-colors"
        >
          <option value="">All types</option>
          {DOC_TYPES.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>

        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["template-library"] })}
          className="p-2 bg-white border border-[#e2ede9] rounded-xl text-[#9ca3af] hover:text-[#111827] transition-colors"
          title="Refresh"
        >
          <RefreshCw size={13} />
        </button>
      </div>

      {/* New template banner */}
      <AnimatePresence>
        {newTemplate && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-4"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-mono text-[#f59e0b] uppercase tracking-wider font-bold">
                Just generated
              </span>
              <button
                onClick={() => setNewTemplate(null)}
                className="text-[#9ca3af] hover:text-[#111827]"
              >
                <X size={13} />
              </button>
            </div>
            <TemplateCard t={newTemplate} isNew />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Template grid */}
      {templatesQ.isLoading ? (
        <div className="flex items-center justify-center gap-2 py-20 text-[#9ca3af]">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading templates…</span>
        </div>
      ) : templatesQ.isError ? (
        <div className="py-16 text-center text-sm text-[#dc2626]">
          Failed to load templates
        </div>
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-14 h-14 bg-[#f0fdf4] rounded-2xl flex items-center justify-center mb-4">
            <BookOpen size={28} className="text-[#cbd5e1]" />
          </div>
          <h3 className="text-sm font-bold text-[#111827] mb-1">No templates found</h3>
          <p className="text-xs text-[#9ca3af] mb-4 text-center max-w-xs">
            {Object.values(listParams).some(Boolean)
              ? "No templates match your filters. Try adjusting or generate one."
              : "No templates yet. Generate the first one for your target country and domain."}
          </p>
          <button
            onClick={() => setShowGenModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#047857] text-white rounded-xl text-xs font-bold hover:bg-[#065f46] transition-all"
          >
            <Plus size={12} />
            Generate Template
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {templates.map((t) => (
            <TemplateCard key={t.id} t={t} />
          ))}
        </div>
      )}

      {/* ── Generate Modal ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showGenModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
          >
            <div className="absolute inset-0 bg-black/30" onClick={() => setShowGenModal(false)} />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden"
            >
              <div className="flex items-center justify-between px-6 py-4 border-b border-[#e2ede9]">
                <div>
                  <h2 className="text-base font-bold text-[#111827]">Generate Template</h2>
                  <p className="text-[11px] text-[#9ca3af] mt-0.5">AI creates a regulatory document from scratch</p>
                </div>
                <button onClick={() => setShowGenModal(false)} className="text-[#9ca3af] hover:text-[#111827]">
                  <X size={18} />
                </button>
              </div>

              <div className="px-6 py-5 space-y-4 max-h-[70vh] overflow-y-auto">
                {/* Domain cards */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2">
                    Regulatory domain *
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {DOMAINS.map((d) => {
                      const Icon = d.icon;
                      const sel = genDomain === d.value;
                      return (
                        <button
                          key={d.value}
                          type="button"
                          onClick={() => setGenDomain(d.value)}
                          className={cn(
                            "flex items-center gap-2 p-2.5 rounded-xl border-2 text-left transition-all",
                            sel ? "border-[#047857] bg-[#ecfdf5]" : "border-[#e2ede9] hover:border-[#a7f3d0]",
                            d.value === "TRADITIONAL" && "col-span-2",
                          )}
                        >
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                            style={{ background: `${d.color}15`, border: `1px solid ${d.color}30` }}
                          >
                            <Icon size={14} style={{ color: d.color }} />
                          </div>
                          <span className={cn("text-xs font-semibold", sel ? "text-[#047857]" : "text-[#111827]")}>
                            {d.label}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Country */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1.5">
                    Country *
                  </label>
                  <SearchableMultiSelect
                    options={COUNTRIES}
                    selected={genCountry}
                    onChange={(sel) => setGenCountry(sel.length > 1 ? [sel[sel.length - 1]] : sel)}
                    placeholder="Search countries…"
                  />
                </div>

                {/* Document type */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
                    Document type *
                  </label>
                  <select
                    value={genDocType}
                    onChange={(e) => setGenDocType(e.target.value)}
                    className="w-full px-3 py-2.5 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors"
                  >
                    <option value="">Select type…</option>
                    {DOC_TYPES.map((d) => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>

                {/* Product name */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
                    Product name
                    <span className="ml-1 normal-case font-normal">(optional)</span>
                  </label>
                  <input
                    value={genProductName}
                    onChange={(e) => setGenProductName(e.target.value)}
                    placeholder="e.g. CardioStent Pro"
                    className="w-full px-3 py-2.5 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors"
                  />
                </div>

                {generateMut.isPending && (
                  <div className="flex items-center gap-2 py-2 text-[#047857]">
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-xs font-semibold">Generating template using AI…</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#e2ede9] bg-[#f7faf9]">
                <button
                  onClick={() => setShowGenModal(false)}
                  className="px-4 py-2 text-sm text-[#6b7280] hover:text-[#111827] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => generateMut.mutate()}
                  disabled={!genDomain || !genCountry[0] || !genDocType || generateMut.isPending}
                  className={cn(
                    "flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all",
                    !genDomain || !genCountry[0] || !genDocType || generateMut.isPending
                      ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
                      : "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]",
                  )}
                >
                  {generateMut.isPending ? (
                    <><Loader2 size={13} className="animate-spin" />Generating…</>
                  ) : (
                    <><Plus size={13} />Generate</>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Feedback Modal ─────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showFeedbackModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
          >
            <div className="absolute inset-0 bg-black/30" onClick={() => setShowFeedbackModal(null)} />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="relative bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-[#e2ede9]">
                <div>
                  <h2 className="text-sm font-bold text-[#111827]">Rate this template</h2>
                  <p className="text-[10px] text-[#9ca3af] mt-0.5 truncate max-w-[220px]">
                    {showFeedbackModal.title}
                  </p>
                </div>
                <button onClick={() => setShowFeedbackModal(null)} className="text-[#9ca3af] hover:text-[#111827]">
                  <X size={16} />
                </button>
              </div>

              <div className="px-5 py-4 space-y-4">
                {/* Star rating */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2">
                    Rating *
                  </label>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map((n) => (
                      <button
                        key={n}
                        type="button"
                        onMouseEnter={() => setHoverStar(n)}
                        onMouseLeave={() => setHoverStar(0)}
                        onClick={() => setFbRating(n)}
                        className="transition-transform hover:scale-110"
                      >
                        <Star
                          size={24}
                          className={n <= (hoverStar || fbRating) ? "text-[#f59e0b]" : "text-[#e2ede9]"}
                          fill={n <= (hoverStar || fbRating) ? "#f59e0b" : "#e2ede9"}
                        />
                      </button>
                    ))}
                    {fbRating > 0 && (
                      <span className="text-xs text-[#9ca3af] ml-2">
                        {["", "Poor", "Fair", "Good", "Very good", "Excellent"][fbRating]}
                      </span>
                    )}
                  </div>
                </div>

                {/* Accuracy */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2">
                    Was this accurate?
                  </label>
                  <div className="flex items-center gap-2">
                    {[
                      { label: "Yes",       value: true  },
                      { label: "Partially", value: null  },
                      { label: "No",        value: false },
                    ].map((opt) => (
                      <button
                        key={opt.label}
                        type="button"
                        onClick={() => setFbAccurate(opt.value)}
                        className={cn(
                          "px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all",
                          fbAccurate === opt.value && opt.value !== null
                            ? "bg-[#ecfdf5] border-[#a7f3d0] text-[#047857]"
                            : fbAccurate === opt.value && opt.value === null && fbAccurate !== undefined
                            ? "bg-[#ecfdf5] border-[#a7f3d0] text-[#047857]"
                            : "border-[#e2ede9] text-[#6b7280] hover:border-[#cbd5e1]",
                        )}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Text */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1">
                    Additional notes (optional)
                  </label>
                  <textarea
                    value={fbText}
                    onChange={(e) => setFbText(e.target.value)}
                    rows={3}
                    placeholder="What was incorrect or could be improved?"
                    className="w-full px-3 py-2 bg-white border border-[#e2ede9] rounded-xl text-xs text-[#111827] outline-none focus:border-[#047857] transition-colors resize-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 px-5 py-4 border-t border-[#e2ede9] bg-[#f7faf9]">
                <button
                  onClick={() => setShowFeedbackModal(null)}
                  className="px-4 py-2 text-sm text-[#6b7280] hover:text-[#111827] transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => feedbackMut.mutate({ id: showFeedbackModal.id })}
                  disabled={fbRating === 0 || feedbackMut.isPending}
                  className={cn(
                    "flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all",
                    fbRating === 0 || feedbackMut.isPending
                      ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
                      : "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]",
                  )}
                >
                  {feedbackMut.isPending ? (
                    <><Loader2 size={13} className="animate-spin" />Submitting…</>
                  ) : (
                    "Submit Feedback"
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
