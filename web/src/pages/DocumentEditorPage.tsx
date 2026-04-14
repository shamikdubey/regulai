import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Save, FileText, Loader2, Clock, ChevronDown, ChevronUp,
  Plus, RefreshCw, X, PenLine,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type Draft = {
  id: string;
  title: string;
  content: string;
  doc_type: string;
  jurisdiction: string;
  updated_at: string;
  created_at: string;
};

type DraftListItem = {
  id: string;
  title: string;
  doc_type: string;
  jurisdiction: string;
  updated_at: string;
};

// ── Constants ─────────────────────────────────────────────────────────────────

const DOC_TYPES = [
  "Notice Response",
  "Regulatory Submission",
  "Technical Dossier",
  "Safety Report",
  "Labeling Document",
  "Clinical Summary",
  "Quality Manual",
  "Standard Operating Procedure",
  "Adverse Event Report",
];

const JURISDICTIONS = [
  "US", "EU", "UK", "India", "Japan", "China", "Singapore",
  "Malaysia", "Thailand", "Vietnam", "Indonesia", "South Korea",
  "Australia", "Canada", "Germany", "France",
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function DocumentEditorPage() {
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null);
  const [title, setTitle] = useState("Untitled Document");
  const [content, setContent] = useState("");
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [jurisdiction, setJurisdiction] = useState("US");
  const [showDrafts, setShowDrafts] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const qc = useQueryClient();

  // ── Queries ────────────────────────────────────────────────────────────────

  const draftsQ = useQuery({
    queryKey: ["document-drafts"],
    queryFn: () =>
      getApiClient()
        .get<DraftListItem[]>("/document-editor/drafts")
        .then((r) => r.data),
  });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const saveMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      content: string;
      doc_type: string;
      jurisdiction: string;
    }) => {
      if (activeDraftId) {
        return getApiClient()
          .put<Draft>(`/document-editor/drafts/${activeDraftId}`, payload)
          .then((r) => r.data);
      }
      return getApiClient()
        .post<Draft>("/document-editor/drafts", payload)
        .then((r) => r.data);
    },
    onSuccess: (data) => {
      setActiveDraftId(data.id);
      setIsDirty(false);
      toast.success("Draft saved");
      qc.invalidateQueries({ queryKey: ["document-drafts"] });
    },
    onError: () => toast.error("Failed to save draft"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      getApiClient().delete(`/document-editor/drafts/${id}`),
    onSuccess: () => {
      toast.success("Draft deleted");
      qc.invalidateQueries({ queryKey: ["document-drafts"] });
    },
    onError: () => toast.error("Failed to delete draft"),
  });

  const loadDraftMutation = useMutation({
    mutationFn: (id: string) =>
      getApiClient()
        .get<Draft>(`/document-editor/drafts/${id}`)
        .then((r) => r.data),
    onSuccess: (data) => {
      setActiveDraftId(data.id);
      setTitle(data.title);
      setContent(data.content);
      setDocType(data.doc_type);
      setJurisdiction(data.jurisdiction);
      setIsDirty(false);
      setShowDrafts(false);
      toast.success(`Loaded "${data.title}"`);
    },
    onError: () => toast.error("Failed to load draft"),
  });

  // ── Auto-save (debounced, 2s) ──────────────────────────────────────────────

  useEffect(() => {
    if (!isDirty) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => {
      if (content.trim().length > 0) {
        saveMutation.mutate({ title, content, doc_type: docType, jurisdiction });
      }
    }, 2000);
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, title, docType, jurisdiction, isDirty]);

  const handleContentChange = (val: string) => {
    setContent(val);
    setIsDirty(true);
  };

  const handleNewDraft = () => {
    setActiveDraftId(null);
    setTitle("Untitled Document");
    setContent("");
    setDocType(DOC_TYPES[0]);
    setJurisdiction("US");
    setIsDirty(false);
    setShowDrafts(false);
  };

  const handleManualSave = () => {
    if (!content.trim()) {
      toast.error("Document is empty");
      return;
    }
    saveMutation.mutate({ title, content, doc_type: docType, jurisdiction });
  };

  const wordCount = content
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Page header */}
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-[#eff6ff] border border-[#bfdbfe] rounded-xl flex items-center justify-center flex-shrink-0">
            <PenLine size={18} className="text-[#2563eb]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-bold text-[#0f172a]">Document Editor</h1>
            <p className="text-xs text-[#94a3b8] mt-0.5">
              Draft, edit and AI-review regulatory documents. Use this to write submission letters, technical files, and reports.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={() => setShowDrafts((p) => !p)}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-xs text-[#64748b] hover:text-[#0f172a] hover:border-[#cbd5e1] transition-all shadow-sm"
          >
            <FileText size={13} />
            Drafts
            {showDrafts ? (
              <ChevronUp size={11} />
            ) : (
              <ChevronDown size={11} />
            )}
          </button>
          <button
            onClick={handleNewDraft}
            className="flex items-center gap-1.5 px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-xs text-[#64748b] hover:text-[#0f172a] hover:border-[#cbd5e1] transition-all shadow-sm"
          >
            <Plus size={13} />
            New
          </button>
          <button
            onClick={handleManualSave}
            disabled={saveMutation.isPending}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-xs transition-all",
              saveMutation.isPending
                ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
                : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
            )}
          >
            {saveMutation.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <Save size={13} />
            )}
            Save
          </button>
        </div>
      </div>

      {/* Drafts panel */}
      <AnimatePresence>
        {showDrafts && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mb-5 bg-white border border-[#e2e8f0] rounded-2xl p-4 shadow-sm"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider">
                Saved drafts
              </span>
              <button
                onClick={() =>
                  qc.invalidateQueries({ queryKey: ["document-drafts"] })
                }
                className="text-[#94a3b8] hover:text-[#0f172a] transition-colors"
              >
                <RefreshCw size={12} />
              </button>
            </div>

            {draftsQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-[#94a3b8]">
                <Loader2 size={13} className="animate-spin" />
                <span className="text-xs">Loading…</span>
              </div>
            ) : draftsQ.isError ? (
              <p className="text-xs text-[#dc2626] py-4 text-center">
                Failed to load drafts
              </p>
            ) : (draftsQ.data ?? []).length === 0 ? (
              <div className="py-6 text-center">
                <FileText size={24} className="text-[#e2e8f0] mx-auto mb-2" />
                <p className="text-xs text-[#94a3b8] mb-2">No documents yet</p>
                <button
                  onClick={handleNewDraft}
                  className="text-xs text-[#2563eb] hover:underline"
                >
                  Create your first regulatory document
                </button>
              </div>
            ) : (
              <div className="space-y-1.5 max-h-64 overflow-y-auto">
                {(draftsQ.data ?? []).map((d) => (
                  <div
                    key={d.id}
                    className={cn(
                      "flex items-center justify-between p-2.5 rounded-xl border transition-all",
                      activeDraftId === d.id
                        ? "bg-[#eff6ff] border-[#bfdbfe]"
                        : "border-[#e2e8f0] hover:border-[#cbd5e1]",
                    )}
                  >
                    <button
                      className="flex-1 min-w-0 text-left"
                      onClick={() => loadDraftMutation.mutate(d.id)}
                      disabled={loadDraftMutation.isPending}
                    >
                      <p className="text-xs font-medium text-[#0f172a] truncate">
                        {d.title}
                      </p>
                      <p className="text-[10px] text-[#94a3b8] font-mono mt-0.5">
                        {d.doc_type} · {d.jurisdiction} ·{" "}
                        {new Date(d.updated_at).toLocaleDateString()}
                      </p>
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(d.id)}
                      disabled={deleteMutation.isPending}
                      className="ml-2 p-1 text-[#94a3b8] hover:text-[#dc2626] transition-colors flex-shrink-0"
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Editor meta: title + selectors */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="col-span-3 md:col-span-1">
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
            Document title
          </label>
          <input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setIsDirty(true);
            }}
            className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
          />
        </div>
        <div>
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
            Document type
          </label>
          <select
            value={docType}
            onChange={(e) => {
              setDocType(e.target.value);
              setIsDirty(true);
            }}
            className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
          >
            {DOC_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-[10px] font-mono text-[#94a3b8] mb-1 uppercase tracking-wider">
            Jurisdiction
          </label>
          <select
            value={jurisdiction}
            onChange={(e) => {
              setJurisdiction(e.target.value);
              setIsDirty(true);
            }}
            className="w-full px-3 py-2 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
          >
            {JURISDICTIONS.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Editor area */}
      <div className="bg-white border border-[#e2e8f0] rounded-2xl overflow-hidden shadow-sm">
        <textarea
          value={content}
          onChange={(e) => handleContentChange(e.target.value)}
          placeholder={`Start writing your ${docType} for ${jurisdiction}…\n\nTip: Use clear section headings and reference specific regulations.`}
          rows={24}
          className="w-full px-5 py-4 bg-transparent text-sm text-[#0f172a] outline-none resize-none font-mono leading-relaxed placeholder:text-[#cbd5e1]"
        />

        {/* Status bar */}
        <div className="flex items-center justify-between px-5 py-2.5 border-t border-[#e2e8f0] bg-[#f8fafc]">
          <div className="flex items-center gap-4 text-[10px] font-mono text-[#94a3b8]">
            <span>{wordCount} words</span>
            <span>{content.length} chars</span>
            {activeDraftId && (
              <span className="text-[#2563eb]">ID: {activeDraftId.slice(0, 8)}</span>
            )}
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono">
            {saveMutation.isPending ? (
              <span className="flex items-center gap-1 text-[#94a3b8]">
                <Loader2 size={10} className="animate-spin" />
                Saving…
              </span>
            ) : isDirty ? (
              <span className="flex items-center gap-1 text-[#f59e0b]">
                <Clock size={10} />
                Unsaved
              </span>
            ) : activeDraftId ? (
              <span className="text-[#0d9488]">Saved</span>
            ) : null}
          </div>
        </div>
      </div>

      {/* Keyboard hint */}
      <p className="text-[10px] text-[#cbd5e1] mt-2 text-right font-mono">
        Auto-saves 2s after typing stops
      </p>
    </div>
  );
}
