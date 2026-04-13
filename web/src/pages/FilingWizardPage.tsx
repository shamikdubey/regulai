import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileCheck, Plus, Loader2, CheckSquare, Square,
  ArrowLeft, ClipboardList, RefreshCw,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type Template = {
  id: string;
  label: string;
  country: string;
  domain: string;
  description: string;
  device_class?: string;
  food_category?: string;
};

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

const STATUS_COLORS: Record<string, string> = {
  planning: "#64748b",
  in_progress: "#f59e0b",
  submitted: "#0d9488",
};

// ── Component ─────────────────────────────────────────────────────────────────

export default function FilingWizardPage() {
  const [view, setView] = useState<"wizard" | "tracker">("wizard");
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [productName, setProductName] = useState("");
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const qc = useQueryClient();

  // ── Queries ────────────────────────────────────────────────────────────────

  const templatesQ = useQuery({
    queryKey: ["filing-templates"],
    queryFn: () =>
      getApiClient()
        .get<Template[]>("/filing-wizard/templates")
        .then((r) => r.data),
  });

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
    mutationFn: (payload: { product_name: string; template_id: string }) =>
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

  const handleGenerateChecklist = () => {
    if (!selectedTemplate || !productName.trim()) {
      toast.error("Select a template and enter a product name");
      return;
    }
    createMutation.mutate({
      product_name: productName,
      template_id: selectedTemplate.id,
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
    setSelectedTemplate(null);
    setProductName("");
    setActiveProject(null);
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#0f172a]">Filing Wizard</h1>
          <p className="text-xs text-[#94a3b8] mt-1">
            Generate and track regulatory filing checklists
          </p>
        </div>
        <div className="flex gap-1 bg-[#f8fafc] border border-[#e2e8f0] rounded-xl p-1">
          {(["wizard", "tracker"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn(
                "px-4 py-1.5 rounded-lg text-xs font-bold capitalize transition-all",
                view === v
                  ? "bg-[#2563eb] text-white"
                  : "text-[#94a3b8] hover:text-[#64748b]",
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
            {/* Step indicator */}
            <div className="flex items-center gap-2 mb-6">
              {[1, 2].map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <div
                    className={cn(
                      "w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all",
                      step >= s
                        ? "bg-[#2563eb] text-white"
                        : "bg-[#e2e8f0] text-[#94a3b8]",
                    )}
                  >
                    {s}
                  </div>
                  <span
                    className={cn(
                      "text-xs",
                      step >= s ? "text-[#0f172a]" : "text-[#94a3b8]",
                    )}
                  >
                    {s === 1 ? "Select Template" : "Checklist"}
                  </span>
                  {s < 2 && <div className="w-8 h-px bg-[#e2e8f0]" />}
                </div>
              ))}
            </div>

            {/* ── STEP 1: Template + product name ── */}
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
                    Product name *
                  </label>
                  <input
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    placeholder="e.g. CardioStent Pro"
                    className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-mono text-[#94a3b8] mb-2 uppercase tracking-wider">
                    Filing template
                    {selectedTemplate && (
                      <span className="ml-2 text-[#2563eb] normal-case">
                        — {selectedTemplate.label}
                      </span>
                    )}
                  </label>

                  {templatesQ.isLoading ? (
                    <div className="flex items-center justify-center gap-2 py-10 text-[#94a3b8]">
                      <Loader2 size={14} className="animate-spin" />
                      <span className="text-xs">Loading templates…</span>
                    </div>
                  ) : templatesQ.isError ? (
                    <div className="py-8 text-center text-xs text-[#dc2626]">
                      Failed to load templates
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 max-h-80 overflow-y-auto pr-1">
                      {(templatesQ.data ?? []).map((t) => (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => setSelectedTemplate(t)}
                          className={cn(
                            "text-left p-3 rounded-xl border transition-all",
                            selectedTemplate?.id === t.id
                              ? "bg-[#eff6ff] border-[#bfdbfe]"
                              : "bg-white border-[#e2e8f0] hover:border-[#cbd5e1]",
                          )}
                        >
                          <div className="text-xs font-bold text-[#0f172a] mb-0.5">
                            {t.label}
                          </div>
                          <div className="text-[10px] text-[#64748b]">
                            {t.description}
                          </div>
                          {t.device_class && (
                            <div className="text-[9px] text-[#94a3b8] mt-1 font-mono">
                              {t.device_class}
                            </div>
                          )}
                          {t.food_category && (
                            <div className="text-[9px] text-[#94a3b8] mt-1 font-mono">
                              {t.food_category}
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <button
                  onClick={handleGenerateChecklist}
                  disabled={
                    createMutation.isPending ||
                    !selectedTemplate ||
                    !productName.trim()
                  }
                  className={cn(
                    "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all",
                    createMutation.isPending ||
                      !selectedTemplate ||
                      !productName.trim()
                      ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
                      : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
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
                    className="text-[#94a3b8] hover:text-[#0f172a] transition-colors"
                  >
                    <ArrowLeft size={16} />
                  </button>
                  <div>
                    <h2 className="text-sm font-bold text-[#0f172a]">
                      {activeProject.product_name}
                    </h2>
                    <p className="text-[10px] text-[#94a3b8]">
                      {activeProject.country} ·{" "}
                      {activeProject.domain.replace(/_/g, " ")}
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="bg-white border border-[#e2e8f0] rounded-2xl p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-[#0f172a]">
                      Progress
                    </span>
                    <span className="text-xs font-mono text-[#2563eb]">
                      {activeProject.progress}%
                    </span>
                  </div>
                  <div className="h-2 bg-[#e2e8f0] rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-[#2563eb] rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${activeProject.progress}%` }}
                      transition={{ duration: 0.4, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-[10px] text-[#94a3b8] font-mono mt-1.5">
                    {activeProject.checklist.filter((i) => i.completed).length}/
                    {activeProject.checklist.length} items complete
                  </p>
                </div>

                {/* Checklist items */}
                <div className="space-y-2">
                  <h3 className="text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider">
                    Filing checklist ({activeProject.checklist.length} items)
                  </h3>
                  {activeProject.checklist.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleToggle(item.id, item.completed)}
                      disabled={toggleMutation.isPending}
                      className="w-full flex items-start gap-3 p-3 bg-white border border-[#e2e8f0] rounded-xl hover:border-[#cbd5e1] transition-all text-left shadow-sm"
                    >
                      <div
                        className={cn(
                          "mt-0.5 flex-shrink-0 transition-colors",
                          item.completed
                            ? "text-[#2563eb]"
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
                              ? "text-[#94a3b8] line-through"
                              : "text-[#0f172a]",
                          )}
                        >
                          {item.task}
                        </p>
                        {item.required_document && (
                          <p className="text-[10px] text-[#94a3b8] mt-0.5 font-mono">
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
                        ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
                        : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
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
              <span className="text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider">
                All filing projects
              </span>
              <button
                onClick={() =>
                  qc.invalidateQueries({ queryKey: ["filing-projects"] })
                }
                className="flex items-center gap-1.5 text-xs text-[#94a3b8] hover:text-[#0f172a] transition-colors"
              >
                <RefreshCw size={12} />
                Refresh
              </button>
            </div>

            {projectsQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-16 text-[#94a3b8]">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading projects…</span>
              </div>
            ) : projectsQ.isError ? (
              <div className="py-16 text-center text-sm text-[#dc2626]">
                Failed to load projects
              </div>
            ) : (projectsQ.data ?? []).length === 0 ? (
              <div className="py-16 text-center">
                <ClipboardList
                  size={32}
                  className="text-[#e2e8f0] mx-auto mb-3"
                />
                <p className="text-sm text-[#94a3b8]">
                  No filing projects yet
                </p>
                <button
                  onClick={() => setView("wizard")}
                  className="mt-3 text-xs text-[#2563eb] hover:underline"
                >
                  Start a new filing
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {(projectsQ.data ?? []).map((proj) => (
                  <motion.div
                    key={proj.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white border border-[#e2e8f0] rounded-2xl p-5 shadow-sm"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-sm font-bold text-[#0f172a]">
                          {proj.product_name}
                        </h3>
                        <p className="text-[10px] text-[#94a3b8] mt-0.5 font-mono">
                          {proj.country} · {proj.domain.replace(/_/g, " ")}
                        </p>
                      </div>
                      <span
                        className="text-[10px] font-bold px-2.5 py-1 rounded-full capitalize"
                        style={{
                          background: `${STATUS_COLORS[proj.status] ?? "#64748b"}15`,
                          color: STATUS_COLORS[proj.status] ?? "#64748b",
                        }}
                      >
                        {proj.status.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="h-1.5 bg-[#e2e8f0] rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-[#2563eb] rounded-full transition-all"
                        style={{ width: `${proj.progress}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-[#94a3b8] font-mono">
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
