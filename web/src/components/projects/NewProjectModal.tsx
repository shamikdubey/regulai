import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  X, Loader2, Apple, Activity, Pill, Leaf, Sprout,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import SearchableMultiSelect from "@/components/ui/SearchableMultiSelect";

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

type Project = {
  id: string;
  product_name: string;
  country: string;
  domain: string;
  status: string;
  progress: number;
  checklist: unknown[];
  created_at: string;
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

const DEVICE_CLASSES = ["Class I", "Class II", "Class III"];

const COUNTRIES = [
  "India", "USA", "UK", "EU (European Union)", "China", "Japan",
  "Brazil", "Australia", "Canada", "Singapore", "South Korea",
  "Indonesia", "Thailand", "Malaysia", "Philippines", "UAE",
  "Saudi Arabia", "Turkey", "Israel", "South Africa", "Nigeria",
  "Kenya", "Ghana", "New Zealand", "Mexico", "Argentina",
  "Colombia", "Chile", "Peru", "Switzerland", "Norway", "Russia",
  "Poland", "Kazakhstan", "Vietnam", "Bangladesh", "Pakistan",
  "Sri Lanka", "Myanmar", "Ethiopia",
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function NewProjectModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [productName, setProductName]         = useState("");
  const [selectedDomain, setSelectedDomain]   = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string[]>([]);
  const [deviceClass, setDeviceClass]         = useState("");
  const [errors, setErrors]                   = useState<Record<string, string>>({});

  const templatesQ = useQuery({
    queryKey: ["filing-templates"],
    queryFn: () =>
      getApiClient().get<Template[]>("/filing-wizard/templates").then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: (payload: { product_name: string; template_id: string }) =>
      getApiClient()
        .post<Project>("/filing-wizard/projects", payload)
        .then((r) => r.data),
    onSuccess: (data) => {
      toast.success("Project created");
      onClose();
      navigate(`/projects/${data.id}`);
    },
    onError: () => toast.error("Failed to create project"),
  });

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!productName.trim())      e.productName = "Product name is required";
    if (!selectedDomain)          e.domain      = "Select a domain";
    if (selectedCountry.length === 0) e.country = "Select a target country";
    if (selectedDomain === "MEDICAL_DEVICE" && !deviceClass)
      e.deviceClass = "Select a device class";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  // Country name → API value
  const countryToValue = (label: string): string =>
    label.toLowerCase().replace(/[\s()\/]+/g, "_").replace(/_{2,}/g, "_");

  const handleSubmit = () => {
    if (!validate()) return;
    const templates = templatesQ.data ?? [];
    const countryValue = countryToValue(selectedCountry[0] ?? "");
    const match =
      templates.find(
        (t) =>
          t.domain.toUpperCase() === selectedDomain &&
          t.country.toLowerCase() === countryValue,
      ) ||
      templates.find((t) => t.domain.toUpperCase() === selectedDomain) ||
      templates[0];

    if (!match) {
      toast.error("No matching template found — try a different configuration");
      return;
    }
    createMut.mutate({ product_name: productName.trim(), template_id: match.id });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-xl mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#e2ede9]">
          <div>
            <h2 className="text-base font-bold text-[#111827]">New Project</h2>
            <p className="text-[11px] text-[#9ca3af] mt-0.5">
              Set up a new regulatory filing project
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[#9ca3af] hover:text-[#111827] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Product name */}
          <div>
            <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1.5">
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
                "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857] focus:ring-1 focus:ring-[#047857] transition-colors",
                errors.productName ? "border-[#dc2626]" : "border-[#e2ede9]",
              )}
            />
            {errors.productName && (
              <p className="text-[10px] text-[#dc2626] mt-1">{errors.productName}</p>
            )}
          </div>

          {/* Domain — 5 cards, 2-col grid (last centered via CSS) */}
          <div>
            <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-2">
              Domain *
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              {DOMAINS.map((d) => {
                const Icon = d.icon;
                const sel = selectedDomain === d.value;
                return (
                  <button
                    key={d.value}
                    type="button"
                    onClick={() => {
                      setSelectedDomain(d.value);
                      setErrors((p) => ({ ...p, domain: "" }));
                    }}
                    className={cn(
                      "flex flex-col items-start p-3.5 rounded-xl border-2 text-left transition-all",
                      sel
                        ? "border-[#047857] bg-[#ecfdf5]"
                        : "border-[#e2ede9] hover:border-[#a7f3d0]",
                      /* last item (5th) spans to center in 2-col grid */
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
                    <p
                      className={cn(
                        "text-xs font-bold leading-snug",
                        sel ? "text-[#047857]" : "text-[#111827]",
                      )}
                    >
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

          {/* Conditional: Device class */}
          {selectedDomain === "MEDICAL_DEVICE" && (
            <div>
              <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1.5">
                Device class *
              </label>
              <select
                value={deviceClass}
                onChange={(e) => {
                  setDeviceClass(e.target.value);
                  setErrors((p) => ({ ...p, deviceClass: "" }));
                }}
                className={cn(
                  "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#111827] outline-none focus:border-[#047857]",
                  errors.deviceClass ? "border-[#dc2626]" : "border-[#e2ede9]",
                )}
              >
                <option value="">Select device class</option>
                {DEVICE_CLASSES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              {errors.deviceClass && (
                <p className="text-[10px] text-[#dc2626] mt-1">{errors.deviceClass}</p>
              )}
            </div>
          )}

          {/* Target country — single-select via SearchableMultiSelect */}
          <div>
            <label className="block text-[10px] font-mono text-[#9ca3af] uppercase tracking-wider mb-1.5">
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
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#e2ede9] bg-[#f7faf9]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#6b7280] hover:text-[#111827] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={createMut.isPending || templatesQ.isLoading}
            className={cn(
              "flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all",
              createMut.isPending || templatesQ.isLoading
                ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed"
                : "bg-[#047857] text-white hover:bg-[#065f46] active:scale-[0.98]",
            )}
          >
            {createMut.isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Creating…
              </>
            ) : (
              "Create Project"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
