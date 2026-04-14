import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FolderOpen, Plus, Loader2, ArrowRight } from "lucide-react";
import { getApiClient } from "@/lib/api";
import { cn, JURISDICTION_MAP } from "@/lib/utils";
import NewProjectModal from "@/components/projects/NewProjectModal";

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
  planning:    { label: "Planning",    color: "#64748b" },
  in_progress: { label: "In Progress", color: "#f59e0b" },
  submitted:   { label: "Submitted",   color: "#0d9488" },
  approved:    { label: "Approved",    color: "#2563eb" },
};

const DOMAIN_COLORS: Record<string, string> = {
  FOOD:           "#f59e0b",
  MEDICAL_DEVICE: "#2563eb",
  PHARMA:         "#0d9488",
  NUTRA:          "#8b5cf6",
  food:           "#f59e0b",
  medical_device: "#2563eb",
  pharma:         "#0d9488",
  nutra:          "#8b5cf6",
};

// Pipeline steps shown on each card
const PIPELINE_STEPS = [
  { label: "Gap Analysis", threshold: 0 },
  { label: "Filing",       threshold: 25 },
  { label: "Documents",    threshold: 50 },
  { label: "Review",       threshold: 75 },
];

function getStepState(stepIndex: number, progress: number): "done" | "active" | "idle" {
  const doneLine = (stepIndex + 1) * 25;
  const activeLine = stepIndex * 25;
  if (progress >= doneLine) return "done";
  if (progress >= activeLine) return "active";
  return "idle";
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ProjectsPage() {
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [filterDomain, setFilterDomain] = useState("");
  const [filterStatus, setFilterStatus] = useState("");
  const [filterCountry, setFilterCountry] = useState("");

  const projectsQ = useQuery({
    queryKey: ["filing-projects"],
    queryFn: () =>
      getApiClient()
        .get<Project[]>("/filing-wizard/projects")
        .then((r) => r.data),
  });

  const allProjects: Project[] = projectsQ.data ?? [];

  // Derive unique values for filter dropdowns
  const domains   = [...new Set(allProjects.map((p) => p.domain))];
  const statuses  = [...new Set(allProjects.map((p) => p.status))];
  const countries = [...new Set(allProjects.map((p) => p.country))];

  const filtered = allProjects.filter((p) => {
    if (filterDomain  && p.domain  !== filterDomain)  return false;
    if (filterStatus  && p.status  !== filterStatus)  return false;
    if (filterCountry && p.country !== filterCountry) return false;
    return true;
  });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-[#0f172a]">My Projects</h1>
          <p className="text-xs text-[#94a3b8] mt-1">
            Manage your regulatory filing projects from gap analysis to submission
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#2563eb] text-white rounded-xl text-sm font-bold hover:bg-[#1d4ed8] active:scale-[0.98] transition-all shadow-sm"
        >
          <Plus size={14} />
          New Project
        </button>
      </div>

      {/* Filter bar — only shown when there are projects */}
      {allProjects.length > 0 && (
        <div className="flex items-center gap-3 mb-5 flex-wrap">
          <select
            value={filterDomain}
            onChange={(e) => setFilterDomain(e.target.value)}
            className="text-xs bg-white border border-[#e2e8f0] text-[#64748b] rounded-lg px-3 py-2 outline-none focus:border-[#2563eb] transition-colors"
          >
            <option value="">All domains</option>
            {domains.map((d) => (
              <option key={d} value={d}>
                {d.replace(/_/g, " ")}
              </option>
            ))}
          </select>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs bg-white border border-[#e2e8f0] text-[#64748b] rounded-lg px-3 py-2 outline-none focus:border-[#2563eb] transition-colors"
          >
            <option value="">All statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>

          <select
            value={filterCountry}
            onChange={(e) => setFilterCountry(e.target.value)}
            className="text-xs bg-white border border-[#e2e8f0] text-[#64748b] rounded-lg px-3 py-2 outline-none focus:border-[#2563eb] transition-colors"
          >
            <option value="">All countries</option>
            {countries.map((c) => {
              const info = JURISDICTION_MAP[c];
              return (
                <option key={c} value={c}>
                  {info ? `${info.flag} ${info.label}` : c}
                </option>
              );
            })}
          </select>

          {(filterDomain || filterStatus || filterCountry) && (
            <button
              onClick={() => {
                setFilterDomain("");
                setFilterStatus("");
                setFilterCountry("");
              }}
              className="text-xs text-[#94a3b8] hover:text-[#0f172a] transition-colors"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Content */}
      {projectsQ.isLoading ? (
        <div className="flex items-center justify-center gap-2 py-24 text-[#94a3b8]">
          <Loader2 size={16} className="animate-spin" />
          <span className="text-sm">Loading projects…</span>
        </div>
      ) : projectsQ.isError ? (
        <div className="py-24 text-center">
          <p className="text-sm text-[#dc2626]">Failed to load projects</p>
          <button
            onClick={() => projectsQ.refetch()}
            className="text-xs text-[#2563eb] mt-2 hover:underline"
          >
            Try again
          </button>
        </div>
      ) : allProjects.length === 0 ? (
        /* Empty state */
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-16 h-16 bg-[#f1f5f9] rounded-2xl flex items-center justify-center mb-4">
            <FolderOpen size={32} className="text-[#cbd5e1]" />
          </div>
          <h2 className="text-sm font-bold text-[#0f172a] mb-1">No projects yet</h2>
          <p className="text-xs text-[#94a3b8] mb-5 max-w-xs text-center">
            Create your first project to start tracking your regulatory filing
            pipeline from gap analysis to submission.
          </p>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#2563eb] text-white rounded-xl text-sm font-bold hover:bg-[#1d4ed8] transition-all shadow-sm"
          >
            <Plus size={14} />
            Create your first project
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-sm text-[#94a3b8]">No projects match the selected filters</p>
        </div>
      ) : (
        /* Project cards grid */
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((project, i) => {
            const country = JURISDICTION_MAP[project.country];
            const statusCfg = STATUS_CONFIG[project.status] ?? STATUS_CONFIG.planning;
            const domainColor = DOMAIN_COLORS[project.domain] ?? "#64748b";
            const completedCount = project.checklist.filter((c) => c.completed).length;

            return (
              <motion.div
                key={project.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="bg-white border border-[#e2e8f0] rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-[#cbd5e1] transition-all flex flex-col gap-4"
              >
                {/* Card header */}
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-[#0f172a] truncate">
                      {project.product_name}
                    </h3>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
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
                        <span className="text-[10px] text-[#64748b] flex items-center gap-1">
                          {country.flag} {country.label}
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className="text-[10px] font-bold px-2.5 py-1 rounded-full flex-shrink-0 capitalize"
                    style={{
                      background: `${statusCfg.color}12`,
                      color: statusCfg.color,
                    }}
                  >
                    {statusCfg.label}
                  </span>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] text-[#94a3b8] font-mono">
                      {completedCount}/{project.checklist.length} items
                    </span>
                    <span className="text-[10px] font-mono font-bold text-[#2563eb]">
                      {project.progress}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-[#e2e8f0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#2563eb] rounded-full transition-all"
                      style={{ width: `${project.progress}%` }}
                    />
                  </div>
                </div>

                {/* Pipeline step indicators */}
                <div className="flex items-center gap-2">
                  {PIPELINE_STEPS.map((step, si) => {
                    const state = getStepState(si, project.progress);
                    return (
                      <div key={step.label} className="flex items-center gap-1 flex-1">
                        <div
                          className={cn(
                            "w-4 h-4 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-bold",
                            state === "done"
                              ? "bg-[#0d9488] text-white"
                              : state === "active"
                                ? "bg-[#2563eb] text-white"
                                : "bg-[#e2e8f0] text-[#94a3b8]",
                          )}
                        >
                          {state === "done" ? "✓" : si + 1}
                        </div>
                        <span
                          className={cn(
                            "text-[9px] truncate",
                            state === "done"
                              ? "text-[#0d9488]"
                              : state === "active"
                                ? "text-[#2563eb] font-semibold"
                                : "text-[#cbd5e1]",
                          )}
                        >
                          {step.label}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between pt-1 border-t border-[#f1f5f9]">
                  <span className="text-[10px] text-[#94a3b8] font-mono">
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="flex items-center gap-1.5 text-xs font-bold text-[#2563eb] hover:text-[#1d4ed8] transition-colors"
                  >
                    Continue
                    <ArrowRight size={12} />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* New Project Modal */}
      {showModal && <NewProjectModal onClose={() => setShowModal(false)} />}
    </div>
  );
}
