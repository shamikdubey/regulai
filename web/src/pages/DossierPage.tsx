import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  FileEdit, Download, ChevronDown, ChevronUp, Loader2,
  CheckCircle, AlertCircle, Clock, Copy, Check,
} from "lucide-react";
import toast from "react-hot-toast";
import { api, DossierResponse, DossierSection } from "@/lib/api";
import { cn, JURISDICTIONS, DOMAINS, JURISDICTION_MAP, DOMAIN_MAP } from "@/lib/utils";

const SUBMISSION_TYPES: Record<string, string[]> = {
  pharma:   ["NDA", "ANDA", "CDSCO-NDA", "MAA (EU)", "J-NDA", "ANDS (Canada)"],
  device:   ["510(k)", "PMA", "CE-MDR", "MDR-CDSCO", "MHLW-Japan", "UKCA"],
  food:     ["FSSAI-License", "FDA-FSMA", "EU-Novel-Food", "FSANZ"],
  nutra:    ["FSSAI-Nutra", "DSHEA-USA", "TGA-Listed", "NHPR-NPN", "FOSHU-Japan", "BlueCap-China"],
  ayurveda: ["AYUSH-License", "TGA-Listed", "NHPR-NPN", "EU-THMPD"],
};

const COMPLETENESS_CONFIG = {
  COMPLETE:   { color: "#00d4aa", label: "Complete",    Icon: CheckCircle },
  DRAFT:      { color: "#f5a623", label: "Draft",       Icon: Clock },
  NEEDS_DATA: { color: "#ff4757", label: "Needs Data",  Icon: AlertCircle },
};

export default function DossierPage() {
  const [form, setForm] = useState({
    product_name: "",
    product_type: "pharma",
    jurisdiction: "india",
    submission_type: "CDSCO-NDA",
    product_description: "",
    active_ingredients: "",
    indication_or_use: "",
    manufacturing_site: "",
  });
  const [result, setResult] = useState<DossierResponse | null>(null);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: api.draftDossier,
    onSuccess: (data) => {
      setResult(data);
      setActiveSection(data.sections[0]?.section_id || null);
      toast.success(`Dossier drafted — ${data.sections.length} sections generated`);
    },
    onError: () => toast.error("Dossier generation failed"),
  });

  const availableTypes = SUBMISSION_TYPES[form.product_type] || [];

  const copySection = (id: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
    toast.success("Copied to clipboard");
  };

  const exportAll = () => {
    if (!result) return;
    const text = [
      `# ${result.product_name} — ${result.submission_type} Dossier`,
      `Jurisdiction: ${result.jurisdiction.toUpperCase()}`,
      "",
      "## COVER LETTER",
      result.cover_letter_draft,
      "",
      "## SUBMISSION CHECKLIST",
      ...result.submission_checklist.map((s, i) => `${i + 1}. ${s}`),
      "",
      ...result.sections.flatMap(s => [
        `## ${s.section_id} ${s.title}`,
        `Status: ${s.completeness}`,
        s.missing_data.length ? `Missing: ${s.missing_data.join("; ")}` : "",
        "",
        s.content,
        "",
      ]),
    ].join("\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.product_name.replace(/\s+/g, "_")}_dossier.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex h-full">
      {/* Left form panel */}
      <div className="w-80 flex-shrink-0 border-r border-[#1f2530] overflow-y-auto bg-[#111318]">
        <div className="p-5">
          <h2 className="font-serif text-lg text-[#e8ecf2] mb-1">Dossier Drafting</h2>
          <p className="text-xs text-[#4a5568] mb-5 leading-relaxed">
            AI generates submission-ready dossier sections with regulatory grounding.
          </p>

          <div className="space-y-3.5">
            <Field label="Product Name">
              <input value={form.product_name} onChange={e => setForm(f => ({ ...f, product_name: e.target.value }))}
                placeholder="e.g. Metformin 500mg Tablets" className="input-field" />
            </Field>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Product Type">
                <select value={form.product_type}
                  onChange={e => {
                    const t = e.target.value;
                    setForm(f => ({ ...f, product_type: t, submission_type: SUBMISSION_TYPES[t]?.[0] || "" }));
                  }} className="input-field">
                  {DOMAINS.map(d => <option key={d.value} value={d.value}>{d.label}</option>)}
                </select>
              </Field>
              <Field label="Jurisdiction">
                <select value={form.jurisdiction} onChange={e => setForm(f => ({ ...f, jurisdiction: e.target.value }))}
                  className="input-field">
                  {JURISDICTIONS.map(j => <option key={j.value} value={j.value}>{j.flag} {j.label}</option>)}
                </select>
              </Field>
            </div>

            <Field label="Submission Type">
              <select value={form.submission_type} onChange={e => setForm(f => ({ ...f, submission_type: e.target.value }))}
                className="input-field">
                {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>

            <Field label="Product Description">
              <textarea value={form.product_description}
                onChange={e => setForm(f => ({ ...f, product_description: e.target.value }))}
                placeholder="Full description including mechanism, dosage, route of administration..."
                rows={3} className="input-field resize-none" />
            </Field>

            <Field label="Active Ingredients">
              <input value={form.active_ingredients}
                onChange={e => setForm(f => ({ ...f, active_ingredients: e.target.value }))}
                placeholder="e.g. Metformin HCl 500mg" className="input-field" />
            </Field>

            <Field label="Indication / Intended Use">
              <input value={form.indication_or_use}
                onChange={e => setForm(f => ({ ...f, indication_or_use: e.target.value }))}
                placeholder="e.g. Type 2 diabetes management" className="input-field" />
            </Field>

            <Field label="Manufacturing Site (optional)">
              <input value={form.manufacturing_site}
                onChange={e => setForm(f => ({ ...f, manufacturing_site: e.target.value }))}
                placeholder="e.g. WHO-GMP certified facility, Hyderabad" className="input-field" />
            </Field>

            <button
              onClick={() => mutation.mutate(form)}
              disabled={mutation.isPending || !form.product_name || !form.product_description}
              className={cn(
                "w-full py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all mt-1",
                mutation.isPending || !form.product_name
                  ? "bg-[#1f2530] text-[#4a5568] cursor-not-allowed"
                  : "bg-[#00d4aa] text-black hover:bg-[#00bfa5] active:scale-[0.98]"
              )}
            >
              {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <FileEdit size={14} />}
              {mutation.isPending ? "Drafting…" : "Generate Dossier"}
            </button>
          </div>
        </div>
      </div>

      {/* Right — sections navigator + content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Section list */}
        {result && (
          <div className="w-64 flex-shrink-0 border-r border-[#1f2530] overflow-y-auto bg-[#0a0c10]">
            <div className="p-3 border-b border-[#1f2530] flex items-center justify-between">
              <span className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider">Sections</span>
              <button onClick={exportAll}
                className="flex items-center gap-1 text-[10px] font-mono text-[#00d4aa] hover:text-white transition-colors">
                <Download size={11} /> Export
              </button>
            </div>
            {/* Cover letter */}
            <button
              onClick={() => setActiveSection("cover")}
              className={cn(
                "w-full text-left px-3 py-2.5 text-xs transition-colors border-b border-[#1f2530]",
                activeSection === "cover" ? "bg-[rgba(0,212,170,0.08)] text-[#00d4aa]" : "text-[#8892a4] hover:bg-[#111318]"
              )}
            >
              Cover Letter
            </button>
            {/* Checklist */}
            <button
              onClick={() => setActiveSection("checklist")}
              className={cn(
                "w-full text-left px-3 py-2.5 text-xs transition-colors border-b border-[#1f2530]",
                activeSection === "checklist" ? "bg-[rgba(0,212,170,0.08)] text-[#00d4aa]" : "text-[#8892a4] hover:bg-[#111318]"
              )}
            >
              Submission Checklist
            </button>
            {/* Content sections */}
            {result.sections.map(s => {
              const cfg = COMPLETENESS_CONFIG[s.completeness];
              return (
                <button key={s.section_id}
                  onClick={() => setActiveSection(s.section_id)}
                  className={cn(
                    "w-full text-left px-3 py-2.5 border-b border-[#1f2530] transition-colors",
                    activeSection === s.section_id ? "bg-[rgba(0,212,170,0.08)]" : "hover:bg-[#111318]"
                  )}
                >
                  <div className="flex items-center gap-2">
                    <cfg.Icon size={10} style={{ color: cfg.color, flexShrink: 0 }} />
                    <span className="text-xs text-[#8892a4] leading-snug truncate">{s.section_id} {s.title}</span>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {/* Content viewer */}
        <div className="flex-1 overflow-y-auto p-6">
          {!result && !mutation.isPending && (
            <div className="flex flex-col items-center justify-center h-full text-[#4a5568]">
              <FileEdit size={40} className="mb-4 opacity-30" />
              <p className="text-sm font-mono">Configure your product and generate a dossier</p>
              <p className="text-xs mt-2 text-center max-w-xs leading-relaxed">
                The AI will draft all required sections with [DATA REQUIRED] placeholders where your actual data needs to go
              </p>
            </div>
          )}

          {mutation.isPending && (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 size={32} className="animate-spin text-[#00d4aa] mb-4" />
              <p className="text-sm text-[#e8ecf2]">Generating dossier sections…</p>
              <p className="text-xs text-[#4a5568] mt-2">This may take 30–60 seconds</p>
            </div>
          )}

          {result && activeSection === "cover" && (
            <SectionView
              title="Cover Letter"
              content={result.cover_letter_draft}
              completeness="DRAFT"
              missing_data={[]}
              sectionId="cover"
              onCopy={() => copySection("cover", result.cover_letter_draft)}
              copied={copied === "cover"}
            />
          )}

          {result && activeSection === "checklist" && (
            <div className="max-w-2xl">
              <h3 className="font-serif text-lg text-[#e8ecf2] mb-4">Submission Checklist</h3>
              <div className="space-y-2">
                {result.submission_checklist.map((item, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[#111318] border border-[#1f2530]">
                    <div className="w-5 h-5 rounded border border-[#2a3040] flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-[#8892a4]">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result && result.sections.find(s => s.section_id === activeSection) && (() => {
            const s = result.sections.find(s => s.section_id === activeSection)!;
            return (
              <SectionView
                title={`${s.section_id} — ${s.title}`}
                content={s.content}
                completeness={s.completeness}
                missing_data={s.missing_data}
                sectionId={s.section_id}
                onCopy={() => copySection(s.section_id, s.content)}
                copied={copied === s.section_id}
              />
            );
          })()}
        </div>
      </div>

      <style>{`
        .input-field {
          width: 100%; padding: 7px 10px; border-radius: 7px;
          background: #181c24; border: 1px solid #2a3040;
          color: #e8ecf2; font-size: 12px; outline: none;
          transition: border-color 0.15s; font-family: inherit;
        }
        .input-field:focus { border-color: #00d4aa; }
        .input-field::placeholder { color: #4a5568; }
        select.input-field option { background: #181c24; }
      `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1">{label}</label>
      {children}
    </div>
  );
}

function SectionView({ title, content, completeness, missing_data, sectionId, onCopy, copied }: {
  title: string; content: string; completeness: string;
  missing_data: string[]; sectionId: string; onCopy: () => void; copied: boolean;
}) {
  const cfg = COMPLETENESS_CONFIG[completeness as keyof typeof COMPLETENESS_CONFIG] || COMPLETENESS_CONFIG.DRAFT;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-lg text-[#e8ecf2]">{title}</h3>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-xs font-mono px-2 py-1 rounded"
            style={{ color: cfg.color, background: `${cfg.color}15`, border: `1px solid ${cfg.color}40` }}>
            <cfg.Icon size={10} /> {cfg.label}
          </span>
          <button onClick={onCopy}
            className="flex items-center gap-1.5 text-xs text-[#4a5568] hover:text-[#00d4aa] transition-colors">
            {copied ? <Check size={12} className="text-[#00d4aa]" /> : <Copy size={12} />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      {missing_data.length > 0 && (
        <div className="mb-4 p-3 rounded-lg bg-[rgba(255,71,87,0.06)] border border-[rgba(255,71,87,0.2)]">
          <p className="text-[10px] font-mono text-[#ff4757] uppercase tracking-widest mb-2">Missing Data Required</p>
          <ul className="space-y-1">
            {missing_data.map((m, i) => <li key={i} className="text-xs text-[#8892a4]">• {m}</li>)}
          </ul>
        </div>
      )}

      <div className="p-5 rounded-xl bg-[#111318] border border-[#1f2530]">
        <pre className="text-xs text-[#8892a4] leading-relaxed whitespace-pre-wrap font-sans"
          dangerouslySetInnerHTML={{
            __html: content.replace(
              /\[DATA REQUIRED: ([^\]]+)\]/g,
              '<span style="color:#f5a623;background:rgba(245,166,35,0.1);padding:1px 6px;border-radius:4px;border:1px solid rgba(245,166,35,0.3)">[DATA REQUIRED: $1]</span>'
            )
          }}
        />
      </div>
    </div>
  );
}
