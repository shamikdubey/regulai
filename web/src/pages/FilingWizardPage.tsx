import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileCheck, Plus, Loader2, CheckSquare, Square,
  ArrowLeft, ClipboardList, RefreshCw, Wand2, ArrowRight,
  Apple, Activity, Pill, Leaf, Sprout,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import SearchableMultiSelect from "@/components/ui/SearchableMultiSelect";

// ── Types ─────────────────────────────────────────────────────────────────────

type ChecklistItem = {
  id: string;
  task: string;
  completed: boolean;
  required_document?: string;
};

type Project = {
  id: string;
  product_name: string;
  country: string;
  domain: string;
  device_class?: string;
  food_category?: string;
  status: "planning" | "in_progress" | "submitted";
  progress: number;
  checklist: ChecklistItem[];
  created_at: string;
  submission_date?: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const DOMAINS = [
  {
    value: "FOOD",
    label: "Food & Food Additives",
    icon: Apple,
    color: "#f59e0b",
    desc: "Food products, beverages, food additives",
  },
  {
    value: "MEDICAL_DEVICE",
    label: "Medical Devices",
    icon: Activity,
    color: "#047857",
    desc: "Class I, II, or III medical devices",
  },
  {
    value: "PHARMA",
    label: "Pharmaceuticals/APIs",
    icon: Pill,
    color: "#7c3aed",
    desc: "Drugs, APIs, biologics, generics",
  },
  {
    value: "NUTRACEUTICAL",
    label: "Nutraceuticals/Supplements",
    icon: Leaf,
    color: "#0d9488",
    desc: "Dietary supplements, vitamins, minerals",
  },
  {
    value: "TRADITIONAL",
    label: "Ayurveda/Traditional Medicine",
    icon: Sprout,
    color: "#92400e",
    desc: "Ayurveda, Unani, Siddha, herbal drugs",
  },
];

const DEVICE_CLASSES = [
  "Class A (Low Risk)",
  "Class B (Low-Moderate Risk)",
  "Class C (Moderate-High Risk)",
  "Class D (High Risk)",
  "Class I (US FDA)",
  "Class II (US FDA)",
  "Class III (US FDA)",
  "Class IIa (EU MDR)",
  "Class IIb (EU MDR)",
  "Class III (EU MDR)",
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

const STATUS_COLORS: Record<string, string> = {
  planning: "#6b7280",
  in_progress: "#f59e0b",
  submitted: "#0d9488",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function FilingWizardPage() {
  const [view, setView]               = useState<"wizard" | "tracker">("wizard");
  const [step, setStep]               = useState(1);
  const [productName, setProductName] = useState("");
  const [domain, setDomain]           = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string[]>([]);
  const [deviceClass, setDeviceClass] = useState("");
  const [foodCategory, setFoodCategory] = useState("");
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const qc = useQueryClient();

  // ── Queries ────────────────────────────────────────────────────────────────

  const projectsQ = useQuery({
    queryKey: ["filing-projects"],
    queryFn: () =>
      getApiClient()
        .get<Project[]>("/filing-wizard/projects")
        .then((r) => r.data),
    enabled: view === "tracker",
  });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const createMutation = useMutation({
    mutationFn: (payload: {
      product_name: string;
      country: string;
      domain: string;
      device_class: string | null;
      food_category: string | null;
    }) =>
      getApiClient()
        .post<Project>("/filing-wizard/projects", payload)
        .then((r) => r.data),
    onSuccess: (data) => {
      setActiveProject(data);
      setStep(2);
      toast.success("Checklist generated");
      qc.invalidateQueries({ queryKey: ["filing-projects"] });
    },
    onError: () => toast.error("Failed to generate checklist"),
  });

  const toggleMutation = useMutation({
    mutationFn: ({
      projectId,
      itemId,
      completed,
    }: {
      projectId: string;
      itemId: string;
      completed: boolean;
    }) =>
      getApiClient()
        .patch<Project>(
          `/filing-wizard/projects/${projectId}/checklist/${itemId}`,
          { completed },
        )
        .then((r) => r.data),
    onSuccess: (data) => setActiveProject(data),
    onError: () => toast.error("Failed to update item"),
  });

  const submitMutation = useMutation({
    mutationFn: (projectId: string) =>
      getApiClient()
        .post<Project>(`/filing-wizard/projects/${projectId}/submit`)
        .then((r) => r.data),
    onSuccess: (data) => {
      setActiveProject(data);
      toast.success("Project marked as submitted!");
      qc.invalidateQueries({ queryKey: ["filing-projects"] });
    },
    onError: () => toast.error("Failed to submit project"),
  });

  // ── Handlers ───────────────────────────────────────────────────────────────

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!productName.trim())           e.productName = "Product name is required";
    if (!domain)                        e.domain      = "Select a regulatory domain";
    if (selectedCountry.length === 0)  e.country     = "Select a target country";
    if (domain === "MEDICAL_DEVICE" && !deviceClass)
      e.deviceClass = "Select a device class";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleGenerateChecklist = () => {
    if (!validate()) return;
    createMutation.mutate({
      product_name: productName.trim(),
      country: selectedCountry[0],
      domain: domain!,
      device_class: deviceClass || null,
      food_category: foodCategory.trim() || null,
    });
  };

  const handleToggle = (itemId: string, current: boolean) => {
    if (!activeProject) return;
    toggleMutation.mutate({
      projectId: activeProject.id,
      itemId,
      completed: !current,
    });
  };

  const resetWizard = () => {
    setStep(1);
    setProductName("");
    setDomain(null);
    setSelectedCountry([]);
    setDeviceClass("");
    setFoodCategory("");
    setActiveProject(null);
    setErrors({});
  };

  const canSubmit =
    !createMutation.isPending &&
    !!domain &&
    selectedCountry.length > 0 &&
    !!productName.trim() &&
    (domain !== "MEDICAL_DEVICE" || !!deviceClass);

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-[#ecfdf5] border border-[#a7f3d0] rounded-xl flex items-center justify-center flex-shrink-0">
            <Wand2 size={18} className="text-[#047857]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-[#111827]">Filing Wizard</h1>
            <p className="text-xs text-[#9ca3af] mt-0.5">
              Step-by-step guidance for regulatory submissions. Start here when you're ready to file in a new country.
            </p>
          </div>
        </div>
        <div className="flex gap-1 bg-[#f7faf9] border border-[#e2ede9] rounded-xl p-1 flex-shrink-0">
          {(["wizard", "tracker"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                "px-4 py-1.5 rounded-lg text-xs font-bold capitalize transition-all",
                view === v
                  ? "bg-[#047857] text-white"
                  : "text-[#9ca3af] hover:text-[#6b7280]",
              )}
            >
              {v === "wizard" ? "New Filing" : "My Projects"}
            </button>
          ))}
        </div>
      </div>

      <AnimatePresence mode="wait">
        {/* ── WIZARD VIEW ─────────────────────────────────────────────────── */}
        {view === "wizard" && (
          <motion.div
            key="wizard"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            {/* Recommended workflow */}
            <div className="mb-5 p-3.5 bg-[#f7faf9] border border-[#e2ede9] rounded-xl">
              <p className="text-[9px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2.5">Recommended workflow</p>
              <div className="flex items-center gap-1.5 flex-wrap">
                {[
                  { label: "Gap Assessment", to: "/gap-assessment" },
                  { label: "Filing Wizard", to: "/filing-wizard" },
                  { label: "Document Editor", to: "/document-editor" },
                  { label: "Compliance Review", to: "/compliance-review" },
                ].map((wfStep, i, arr) => (
                  <div key={wfStep.to} className="flex items-center gap-1.5">
                    <Link
                      to={wfStep.to}
                      className={cn(
                        "text-xs px-2 py-1 rounded-lg font-semibold transition-colors",
                        wfStep.to === "/filing-wizard"
                          ? "bg-[#ecfdf5] border border-[#a7f3d0] text-[#047857]"
                          : "text-[#6b7280] hover:text-[#047857]",
                      )}
                    >
                      {wfStep.label}
                    </Link>
                    {i < arr.length - 1 && (
                      <ArrowRight size={11} className="text-[#cbd5e1] flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* How it works */}
            <div className="mb-5 p-4 bg-[#f7faf9] border border-[#e2ede9] rounded-xl">
              <p className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-3">How it works</p>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { n: 1, title: "Configure your filing", desc: "Pick your target country, domain and product details" },
                  { n: 2, title: "Generate checklist", desc: "AI creates your filing requirements automatically" },
                  { n: 3, title: "Track progress", desc: "Check off items as you complete your submission" },
                ].map((s) => (
                  <div key={s.n} className="flex items-start gap-2.5">
                    <div className="w-5 h-5 rounded-full bg-[#ecfdf5] text-[#047857] text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                      {s.n}
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-[#111827]">{s.title}</p>
                      <p className="text-[10px] text-[#6b7280] mt-0.5">{s.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-6">
              {[1, 2].map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all",
                      step >= s
                        ? "bg-[#047857] text-white"
                        : "bg-[#e2ede9] text-[#9ca3af]",
                    )}
                  >
                    {s}
                  </div>
                  <span
                    className={cn(
                      "text-xs",
                      step >= s ? "text-[#111827]" : "text-[#9ca3af]",
                    )}
                  >
                    {s === 1 ? "Configure Filing" : "Checklist"}
                  </span>
                  {s < 2 && <div className="w-8 h-px bg-[#e2ede9]" />}
                </div>
              ))}
            </div>

            {/* ── STEP 1: Configure filing ── */}
            {step === 1 && (
              <div className="space-y-5">

                {/* A) Product name */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
                    Product name *
                  </label>
                  <input
                    value={productName}
                    onChange={(e) => {
                      setProductName(e.target.value);
                      setErrors((p) => ({ ...p, productName: "" }));
                    }}
                    placeholder="e.g. CardioStent Pro, VitaFlex Capsules"
                    className={cn(
                      "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors",
                      errors.productName ? "border-[#dc2626]" : "border-[#e2ede9]",
                    )}
                  />
                  {errors.productName && (
                    <p className="text-[10px] text-[#dc2626] mt-1">{errors.productName}</p>
                  )}
                </div>

                {/* B) Domain — 5 cards */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] mb-2 uppercase tracking-wider">
                    Regulatory domain *
                  </label>
                  <div className="grid grid-cols-2 gap-2.5">
                    {DOMAINS.map((d) => {
                      const Icon = d.icon;
                      const sel = domain === d.value;
                      return (
                        <button
                          key={d.value}
                          type="button"
                          onClick={() => {
                            setDomain(d.value);
                            setDeviceClass("");
                            setErrors((p) => ({ ...p, domain: "", deviceClass: "" }));
                          }}
                          className={cn(
                            "flex flex-col items-start p-3.5 rounded-xl border-2 text-left transition-all",
                            sel
                              ? "border-[#047857] bg-[#ecfdf5]"
                              : "border-[#e2ede9] hover:border-[#a7f3d0]",
                            d.value === "TRADITIONAL" && "col-span-2 sm:col-span-1 sm:col-start-1",
                          )}
                        >
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center mb-2 flex-shrink-0"
                            style={{
                              background: `${d.color}15`,
                              border: `1px solid ${d.color}30`,
                            }}
                          >
                            <Icon size={16} style={{ color: d.color }} />
                          </div>
                          <p className={cn(
                            "text-xs font-bold leading-snug",
                            sel ? "text-[#047857]" : "text-[#111827]",
                          )}>
                            {d.label}
                          </p>
                          <p className="text-[10px] text-[#9ca3af] mt-0.5">{d.desc}</p>
                        </button>
                      );
                    })}
                  </div>
                  {errors.domain && (
                    <p className="text-[10px] text-[#dc2626] mt-1">{errors.domain}</p>
                  )}
                </div>

                {/* C) Country — searchable single-select */}
                <div>
                  <label className="block text-[10px] font-mono text-[#9ca3af] mb-1.5 uppercase tracking-wider">
                    Target country *
                  </label>
                  <div className={cn(errors.country && "ring-1 ring-[#dc2626] rounded-xl")}>
                    <SearchableMultiSelect
                      options={COUNTRIES}
                      selected={selectedCountry}
                      onChange={(sel) => {
                        // single-select: keep only the last picked item
                        const next = sel.length > 1 ? [sel[sel.length - 1]] : sel;
                        setSelectedCountry(next);
                        setErrors((p) => ({ ...p, country: "" }));
                      }}
                      placeholder="Search countries…"
                    />
                  </div>
                  {errors.country && (
                    <p className="text-[10px] text-[#dc2626] mt-1">{errors.country}</p>
                  )}
                </div>

                {/* D) Device Class (conditional) */}
                {domain === "MEDICAL_DEVICE" && (
                  <div>
                    <label className="block text-[10px] font-mono text-[#9ca3af] mb-1.5 uppercase tracking-wider">
                      Device class *
                    </label>
                    <select
                      value={deviceClass}
                      onChange={(e) => {
                        setDeviceClass(e.target.value);
                        setErrors((p) => ({ ...p, deviceClass: "" }));
                      }}
                      className={cn(
                        "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors",
                        errors.deviceClass ? "border-[#dc2626]" : "border-[#e2ede9]",
                      )}
                    >
                      <option value="">Select device class…</option>
                      {DEVICE_CLASSES.map((c) => (
                        <option key={c} value={c}>{c}</option>
                      ))}
                    </select>
                    {errors.deviceClass && (
                      <p className="text-[10px] text-[#dc2626] mt-1">{errors.deviceClass}</p>
                    )}
                  </div>
                )}

                {/* E) Food Category (conditional) */}
                {(domain === "FOOD" || domain === "NUTRACEUTICAL") && (
                  <div>
                    <label className="block text-[10px] font-mono text-[#9ca3af] mb-1 uppercase tracking-wider">
                      Food / supplement category
                      <span className="ml-1 normal-case text-[#9ca3af] font-normal">(optional)</span>
                    </label>
                    <input
                      value={foodCategory}
                      onChange={(e) => setFoodCategory(e.target.value)}
                      placeholder="e.g. Processed Foods, Dietary Supplements, Beverages"
                      className="w-full px-3 py-2.5 bg-white border border-[#e2ede9] rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] transition-colors"
                    />
                  </div>
                )}

                {/* F) Generate Checklist */}
                <button
                  onClick={handleGenerateChecklist}
                  disabled={!canSubmit}
                  className={cn(
                    "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
                    canSubmit
                      ? "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]"
                      : "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed",
                  )}
                >
                  {createMutation.isPending ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Plus size={14} />
                      Generate Checklist
                    </>
                  )}
                </button>
              </div>
            )}

            {/* ── STEP 2: Checklist ── */}
            {step === 2 && activeProject && (
              <div className="space-y-4">
                {/* Back + project meta */}
                <div className="flex items-center gap-3">
                  <button
                    onClick={resetWizard}
                    className="text-[#9ca3af] hover:text-[#111827] transition-colors"
                  >
                    <ArrowLeft size={16} />
                  </button>
                  <div>
                    <h2 className="text-sm font-bold text-[#111827]">
                      {activeProject.product_name}
                    </h2>
                    <p className="text-[10px] text-[#9ca3af]">
                      {activeProject.country} ·{" "}
                      {activeProject.domain.replace(/_/g, " ")}
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="bg-white border border-[#e2ede9] rounded-2xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-[#111827]">
                      Progress
                    </span>
                    <span className="text-xs font-mono text-[#047857]">
                      {activeProject.progress}%
                    </span>
                  </div>
                  <div className="h-2 bg-[#e2ede9] rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-[#047857] rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${activeProject.progress}%` }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-[10px] text-[#9ca3af] font-mono mt-1.5">
                    {activeProject.checklist.filter((i) => i.completed).length}/
                    {activeProject.checklist.length} items complete
                  </p>
                </div>

                {/* Checklist items */}
                <div className="space-y-2">
                  <h3 className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider">
                    Filing checklist ({activeProject.checklist.length} items)
                  </h3>
                  {activeProject.checklist.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleToggle(item.id, item.completed)}
                      disabled={toggleMutation.isPending}
                      className="w-full flex items-start gap-3 p-3 bg-white border border-[#e2ede9] rounded-xl hover:border-[#cbd5e1] transition-all text-left shadow-sm"
                    >
                      <div
                        className={cn(
                          "mt-0.5 flex-shrink-0 transition-colors",
                          item.completed
                            ? "text-[#047857]"
                            : "text-[#cbd5e1]",
                        )}
                      >
                        {item.completed ? (
                          <CheckSquare size={15} />
                        ) : (
                          <Square size={15} />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p
                          className={cn(
                            "text-xs font-medium",
                            item.completed
                              ? "text-[#9ca3af] line-through"
                              : "text-[#111827]",
                          )}
                        >
                          {item.task}
                        </p>
                        {item.required_document && (
                          <p className="text-[10px] text-[#9ca3af] mt-0.5 font-mono">
                            Required: {item.required_document}
                          </p>
                        )}
                      </div>
                    </button>
                  ))}
                </div>

                {/* Submit / submitted */}
                {activeProject.status !== "submitted" ? (
                  <button
                    onClick={() => submitMutation.mutate(activeProject.id)}
                    disabled={
                      submitMutation.isPending || activeProject.progress < 100
                    }
                    className={cn(
                      "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
                      submitMutation.isPending || activeProject.progress < 100
                        ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
                        : "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]",
                    )}
                  >
                    {submitMutation.isPending ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        Submitting…
                      </>
                    ) : (
                      <>
                        <FileCheck size={14} />
                        Mark as Submitted
                        {activeProject.progress < 100 && (
                          <span className="text-[10px] font-normal opacity-60">
                            (complete all items first)
                          </span>
                        )}
                      </>
                    )}
                  </button>
                ) : (
                  <div className="flex items-center gap-2 px-4 py-3 bg-[#f0fdf9] border border-[#99f6e4] rounded-xl">
                    <FileCheck size={14} className="text-[#0d9488]" />
                    <span className="text-xs font-bold text-[#0d9488]">
                      Filing submitted
                    </span>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        )}

        {/* ── TRACKER VIEW ────────────────────────────────────────────────── */}
        {view === "tracker" && (
          <motion.div
            key="tracker"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <div className="flex items-center justify-between mb-4">
              <span className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider">
                All filing projects
              </span>
              <button
                onClick={() =>
                  qc.invalidateQueries({ queryKey: ["filing-projects"] })
                }
                className="flex items-center gap-1.5 text-xs text-[#9ca3af] hover:text-[#111827] transition-colors"
              >
                <RefreshCw size={12} />
                Refresh
              </button>
            </div>

            {projectsQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-16 text-[#9ca3af]">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading projects…</span>
              </div>
            ) : projectsQ.isError ? (
              <div className="py-16 text-center text-sm text-[#dc2626]">
                Failed to load projects
              </div>
            ) : (projectsQ.data ?? []).length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="w-14 h-14 bg-[#f0fdf4] rounded-2xl flex items-center justify-center mb-4">
                  <ClipboardList size={28} className="text-[#cbd5e1]" />
                </div>
                <h3 className="text-sm font-bold text-[#111827] mb-1">No filing projects yet</h3>
                <p className="text-xs text-[#9ca3af] mb-4 max-w-xs text-center">
                  Create your first project to get started with your regulatory submission.
                </p>
                <button
                  onClick={() => setView("wizard")}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#047857] text-white rounded-xl text-xs font-bold hover:bg-[#065f46] transition-all"
                >
                  <Plus size={12} />
                  Create first project
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {(projectsQ.data ?? []).map((proj) => (
                  <motion.div
                    key={proj.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white border border-[#e2ede9] rounded-2xl p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-bold text-[#111827]">
                          {proj.product_name}
                        </h3>
                        <p className="text-[10px] text-[#9ca3af] mt-0.5 font-mono">
                          {proj.country} · {proj.domain.replace(/_/g, " ")}
                        </p>
                      </div>
                      <span
                        className="text-[10px] font-bold px-2.5 py-1 rounded-full capitalize"
                        style={{
                          background: `${STATUS_COLORS[proj.status] ?? "#6b7280"}15`,
                          color: STATUS_COLORS[proj.status] ?? "#6b7280",
                        }}
                      >
                        {proj.status.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="h-1.5 bg-[#e2ede9] rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-[#047857] rounded-full transition-all"
                        style={{ width: `${proj.progress}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-[#9ca3af] font-mono">
                      <span>
                        {proj.checklist.filter((i) => i.completed).length}/
                        {proj.checklist.length} items complete
                      </span>
                      <span>{proj.progress}%</span>
                    </div>

                    {proj.submission_date && (
                      <p className="text-[10px] text-[#0d9488] mt-2 font-mono">
                        Submitted: {proj.submission_date}
                      </p>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
