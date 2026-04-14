import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft, Loader2, CheckSquare, Square, BarChart2,
  ClipboardList, FileEdit, ShieldCheck, ArrowRight,
  RefreshCw, Wand2, PenLine,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn, JURISDICTION_MAP } from "@/lib/utils";

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
  status: "planning" | "in_progress" | "submitted" | "approved";
  progress: number;
  checklist: ChecklistItem[];
  created_at: string;
  submission_date?: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  planning:    { label: "Planning",    color: "#6b7280" },
  in_progress: { label: "In Progress", color: "#f59e0b" },
  submitted:   { label: "Submitted",   color: "#0d9488" },
  approved:    { label: "Approved",    color: "#047857" },
};

const DOMAIN_COLORS: Record<string, string> = {
  FOOD: "#f59e0b", food: "#f59e0b",
  MEDICAL_DEVICE: "#047857", medical_device: "#047857",
  PHARMA: "#0d9488", pharma: "#0d9488",
  NUTRA: "#8b5cf6", nutra: "#8b5cf6",
};

// Pipeline tab definitions
const PIPELINE_TABS = [
  { id: "gap",       label: "Gap Analysis",      icon: BarChart2 },
  { id: "checklist", label: "Filing Checklist",  icon: ClipboardList },
  { id: "documents", label: "Documents",          icon: FileEdit },
  { id: "review",    label: "Compliance Review",  icon: ShieldCheck },
];

function getTabState(
  tabIndex: number,
  progress: number,
): "done" | "active" | "idle" {
  const done   = (tabIndex + 1) * 25;
  const active = tabIndex * 25;
  if (progress >= done)   return "done";
  if (progress >= active) return "active";
  return "idle";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [activeTab, setActiveTab] = useState("gap");

  // Fetch all projects and find this one — guarantees the endpoint exists
  const projectsQ = useQuery({
    queryKey: ["filing-projects"],
    queryFn: () =>
      getApiClient()
        .get<Project[]>("/filing-wizard/projects")
        .then((r) => r.data),
  });

  const project: Project | undefined = (projectsQ.data ?? []).find(
    (p) => p.id === id,
  );

  // Toggle checklist item
  const toggleMut = useMutation({
    mutationFn: ({
      itemId,
      completed,
    }: {
      itemId: string;
      completed: boolean;
    }) =>
      getApiClient()
        .patch<Project>(
          `/filing-wizard/projects/${id}/checklist/${itemId}`,
          { completed },
        )
        .then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData<Project[]>(["filing-projects"], (old) =>
        (old ?? []).map((p) => (p.id === id ? updated : p)),
      );
    },
    onError: () => toast.error("Failed to update item"),
  });

  // Generate checklist
  const generateMut = useMutation({
    mutationFn: () =>
      getApiClient()
        .post<Project>(`/filing-wizard/projects/${id}/checklist/generate`)
        .then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData<Project[]>(["filing-projects"], (old) =>
        (old ?? []).map((p) => (p.id === id ? updated : p)),
      );
      toast.success("Checklist generated");
    },
    onError: () => toast.error("Failed to generate checklist"),
  });

  // ── Loading / error states ─────────────────────────────────────────────────

  if (projectsQ.isLoading) {
    return (
      <div className="flex items-center justify-center h-full gap-2 text-[#9ca3af]">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading project…</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3">
        <p className="text-sm text-[#111827] font-semibold">Project not found</p>
        <button
          onClick={() => navigate("/projects")}
          className="text-xs text-[#047857] hover:underline"
        >
          ← Back to projects
        </button>
      </div>
    );
  }

  const country    = JURISDICTION_MAP[project.country];
  const statusCfg  = STATUS_CONFIG[project.status] ?? STATUS_CONFIG.planning;
  const domainColor = DOMAIN_COLORS[project.domain] ?? "#6b7280";
  const completedCount = project.checklist.filter((c) => c.completed).length;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-4xl mx-auto">

      {/* Back + header */}
      <div className="flex items-start gap-4 mb-6">
        <button
          onClick={() => navigate("/projects")}
          className="mt-1 text-[#9ca3af] hover:text-[#111827] transition-colors flex-shrink-0"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3 flex-wrap">
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-[#111827] truncate">
                {project.product_name}
              </h1>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                <span
                  className="text-[10px] font-bold px-2 py-0.5 rounded-full"
                  style={{
                    background: `${domainColor}12`,
                    color: domainColor,
                    border: `1px solid ${domainColor}30`,
                  }}
                >
                  {project.domain.replace(/_/g, " ")}
                </span>
                {country && (
                  <span className="text-xs text-[#6b7280]">
                    {country.flag} {country.label}
                  </span>
                )}
                <span
                  className="text-[10px] font-bold px-2.5 py-1 rounded-full capitalize"
                  style={{
                    background: `${statusCfg.color}12`,
                    color: statusCfg.color,
                  }}
                >
                  {statusCfg.label}
                </span>
              </div>
            </div>
          </div>

          {/* Progress */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] text-[#9ca3af] font-mono">
                {completedCount}/{project.checklist.length} checklist items complete
              </span>
              <span className="text-[10px] font-mono font-bold text-[#047857]">
                {project.progress}%
              </span>
            </div>
            <div className="h-2 bg-[#e2ede9] rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-[#047857] rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${project.progress}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline stepper tabs */}
      <div className="flex items-center gap-0 mb-6 bg-white border border-[#e2ede9] rounded-2xl overflow-hidden shadow-sm">
        {PIPELINE_TABS.map((tab, ti) => {
          const state   = getTabState(ti, project.progress);
          const isActive = activeTab === tab.id;
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "flex-1 flex items-center justify-center gap-2 px-3 py-3.5 text-xs font-semibold transition-all border-r last:border-r-0 border-[#e2ede9]",
                isActive
                  ? "bg-[#ecfdf5] text-[#047857]"
                  : "text-[#6b7280] hover:bg-[#f7faf9] hover:text-[#111827]",
              )}
            >
              {/* Step circle */}
              <div
                className={cn(
                  "w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-bold",
                  state === "done"
                    ? "bg-[#0d9488] text-white"
                    : isActive
                      ? "bg-[#047857] text-white"
                      : "bg-[#e2ede9] text-[#9ca3af]",
                )}
              >
                {state === "done" ? "✓" : ti + 1}
              </div>
              <Icon size={13} className="hidden sm:block flex-shrink-0" />
              <span className="hidden sm:block truncate">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      <div className="space-y-4">

        {/* ── Step 1: Gap Analysis ── */}
        {activeTab === "gap" && (
          <div className="space-y-4">
            <div className="bg-white border border-[#e2ede9] rounded-2xl p-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-[#f3f0ff] flex items-center justify-center flex-shrink-0">
                  <BarChart2 size={20} className="text-[#8b5cf6]" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-[#111827] mb-1">
                    Run Gap Assessment
                  </h3>
                  <p className="text-xs text-[#6b7280] leading-relaxed mb-4">
                    Identify compliance gaps for{" "}
                    <strong>{project.product_name}</strong>
                    {country ? ` in ${country.flag} ${country.label}` : ""}.
                    The assessment will highlight requirements, actions needed,
                    and estimated timelines.
                  </p>
                  <button
                    onClick={() =>
                      navigate(
                        `/gap-assessment?product=${encodeURIComponent(project.product_name)}&jurisdiction=${encodeURIComponent(project.country)}`,
                      )
                    }
                    className="flex items-center gap-2 px-4 py-2 bg-[#8b5cf6] text-white rounded-xl text-xs font-bold hover:bg-[#7c3aed] transition-all"
                  >
                    <BarChart2 size={13} />
                    Run Gap Assessment
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-[#f7faf9] border border-[#e2ede9] rounded-xl p-4">
              <p className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2">
                Project info
              </p>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-[10px] text-[#9ca3af]">Domain</p>
                  <p className="font-semibold text-[#111827]">
                    {project.domain.replace(/_/g, " ")}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-[#9ca3af]">Target market</p>
                  <p className="font-semibold text-[#111827]">
                    {country ? `${country.flag} ${country.label}` : project.country}
                  </p>
                </div>
                {project.device_class && (
                  <div>
                    <p className="text-[10px] text-[#9ca3af]">Device class</p>
                    <p className="font-semibold text-[#111827]">{project.device_class}</p>
                  </div>
                )}
                {project.food_category && (
                  <div>
                    <p className="text-[10px] text-[#9ca3af]">Food category</p>
                    <p className="font-semibold text-[#111827]">{project.food_category}</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Step 2: Filing Checklist ── */}
        {activeTab === "checklist" && (
          <div className="space-y-4">
            {project.checklist.length === 0 ? (
              <div className="bg-white border border-[#e2ede9] rounded-2xl p-8 shadow-sm text-center">
                <ClipboardList size={32} className="text-[#e2ede9] mx-auto mb-3" />
                <p className="text-sm font-semibold text-[#111827] mb-1">
                  No checklist yet
                </p>
                <p className="text-xs text-[#9ca3af] mb-4">
                  Generate a checklist tailored to your product domain and target market
                </p>
                <button
                  onClick={() => generateMut.mutate()}
                  disabled={generateMut.isPending}
                  className={cn(
                    "flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold mx-auto transition-all",
                    generateMut.isPending
                      ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
                      : "bg-[#047857] text-white hover:bg-[#065f46]",
                  )}
                >
                  {generateMut.isPending ? (
                    <><Loader2 size={14} className="animate-spin" /> Generating…</>
                  ) : (
                    <><ClipboardList size={14} /> Generate Checklist</>
                  )}
                </button>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider">
                    {project.checklist.length} filing tasks ·{" "}
                    {completedCount} completed
                  </span>
                  <button
                    onClick={() =>
                      qc.invalidateQueries({ queryKey: ["filing-projects"] })
                    }
                    className="flex items-center gap-1 text-xs text-[#9ca3af] hover:text-[#111827] transition-colors"
                  >
                    <RefreshCw size={11} />
                    Refresh
                  </button>
                </div>

                <div className="space-y-2">
                  {project.checklist.map((item) => (
                    <button
                      key={item.id}
                      onClick={() =>
                        toggleMut.mutate({
                          itemId: item.id,
                          completed: !item.completed,
                        })
                      }
                      disabled={toggleMut.isPending}
                      className="w-full flex items-start gap-3 p-3.5 bg-white border border-[#e2ede9] rounded-xl hover:border-[#cbd5e1] transition-all text-left shadow-sm"
                    >
                      <div
                        className={cn(
                          "mt-0.5 flex-shrink-0 transition-colors",
                          item.completed ? "text-[#047857]" : "text-[#cbd5e1]",
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
              </>
            )}
          </div>
        )}

        {/* ── Step 3: Documents ── */}
        {activeTab === "documents" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white border border-[#e2ede9] rounded-2xl p-5 shadow-sm">
                <div className="w-9 h-9 rounded-xl bg-[#ecfdf5] flex items-center justify-center mb-3">
                  <PenLine size={18} className="text-[#047857]" />
                </div>
                <h3 className="text-sm font-bold text-[#111827] mb-1">
                  Document Editor
                </h3>
                <p className="text-xs text-[#6b7280] mb-4">
                  Draft and edit regulatory documents for this filing
                </p>
                <button
                  onClick={() =>
                    navigate(
                      `/document-editor?project=${encodeURIComponent(project.id)}&product=${encodeURIComponent(project.product_name)}`,
                    )
                  }
                  className="flex items-center gap-1.5 text-xs font-bold text-[#047857] hover:text-[#065f46] transition-colors"
                >
                  Open editor <ArrowRight size={12} />
                </button>
              </div>

              <div className="bg-white border border-[#e2ede9] rounded-2xl p-5 shadow-sm">
                <div className="w-9 h-9 rounded-xl bg-[#f0fdf9] flex items-center justify-center mb-3">
                  <Wand2 size={18} className="text-[#0d9488]" />
                </div>
                <h3 className="text-sm font-bold text-[#111827] mb-1">
                  Dossier Drafting
                </h3>
                <p className="text-xs text-[#6b7280] mb-4">
                  AI-generate a technical submission dossier
                </p>
                <button
                  onClick={() =>
                    navigate(
                      `/dossier?product=${encodeURIComponent(project.product_name)}&jurisdiction=${encodeURIComponent(project.country)}`,
                    )
                  }
                  className="flex items-center gap-1.5 text-xs font-bold text-[#0d9488] hover:text-[#0f766e] transition-colors"
                >
                  Draft dossier <ArrowRight size={12} />
                </button>
              </div>
            </div>

            <div className="bg-[#f7faf9] border border-[#e2ede9] rounded-xl p-4 text-center">
              <p className="text-xs text-[#9ca3af]">
                Documents created in the editor or dossier tool will appear here
                once document-level project linking is enabled.
              </p>
            </div>
          </div>
        )}

        {/* ── Step 4: Compliance Review ── */}
        {activeTab === "review" && (
          <div className="space-y-4">
            <div className="bg-white border border-[#e2ede9] rounded-2xl p-6 shadow-sm">
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-[#fff7ed] flex items-center justify-center flex-shrink-0">
                  <ShieldCheck size={20} className="text-[#f59e0b]" />
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-bold text-[#111827] mb-1">
                    Compliance Review
                  </h3>
                  <p className="text-xs text-[#6b7280] leading-relaxed mb-4">
                    Upload your drafted document to run an AI compliance review.
                    Get a compliance score, findings list, and actionable
                    recommendations before submission.
                  </p>
                  <button
                    onClick={() => navigate("/compliance-review")}
                    className="flex items-center gap-2 px-4 py-2 bg-[#f59e0b] text-white rounded-xl text-xs font-bold hover:bg-[#d97706] transition-all"
                  >
                    <ShieldCheck size={13} />
                    Run Compliance Review
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            </div>

            {project.status === "submitted" && (
              <div className="flex items-center gap-3 px-5 py-3.5 bg-[#f0fdf9] border border-[#99f6e4] rounded-xl">
                <ShieldCheck size={16} className="text-[#0d9488]" />
                <div>
                  <p className="text-xs font-bold text-[#0d9488]">
                    Filing submitted
                  </p>
                  {project.submission_date && (
                    <p className="text-[10px] text-[#0d9488] font-mono">
                      {project.submission_date}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
