import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { X, Loader2, Search, ShoppingCart, Activity } from "lucide-react";
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
    label: "Food Product",
    icon: ShoppingCart,
    color: "#f59e0b",
    desc: "Food, beverage, nutraceutical",
  },
  {
    value: "MEDICAL_DEVICE",
    label: "Medical Device",
    icon: Activity,
    color: "#2563eb",
    desc: "Class I, II, or III devices",
  },
];

const DEVICE_CLASSES = ["Class I", "Class II", "Class III"];

const COUNTRIES = [
  { value: "india",        label: "India",          flag: "🇮🇳" },
  { value: "usa",          label: "United States",  flag: "🇺🇸" },
  { value: "eu",           label: "European Union", flag: "🇪🇺" },
  { value: "china",        label: "China",          flag: "🇨🇳" },
  { value: "japan",        label: "Japan",          flag: "🇯🇵" },
  { value: "uk",           label: "United Kingdom", flag: "🇬🇧" },
  { value: "australia",    label: "Australia",      flag: "🇦🇺" },
  { value: "canada",       label: "Canada",         flag: "🇨🇦" },
  { value: "brazil",       label: "Brazil",         flag: "🇧🇷" },
  { value: "singapore",    label: "Singapore",      flag: "🇸🇬" },
  { value: "south_korea",  label: "South Korea",    flag: "🇰🇷" },
  { value: "malaysia",     label: "Malaysia",       flag: "🇲🇾" },
  { value: "thailand",     label: "Thailand",       flag: "🇹🇭" },
  { value: "indonesia",    label: "Indonesia",      flag: "🇮🇩" },
  { value: "saudi_arabia", label: "Saudi Arabia",   flag: "🇸🇦" },
  { value: "uae",          label: "UAE",            flag: "🇦🇪" },
  { value: "south_africa", label: "South Africa",   flag: "🇿🇦" },
  { value: "turkey",       label: "Turkey",         flag: "🇹🇷" },
  { value: "russia",       label: "Russia",         flag: "🇷🇺" },
  { value: "mexico",       label: "Mexico",         flag: "🇲🇽" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function NewProjectModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const [productName, setProductName]         = useState("");
  const [selectedDomain, setSelectedDomain]   = useState<string | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [countrySearch, setCountrySearch]     = useState("");
  const [deviceClass, setDeviceClass]         = useState("");
  const [foodCategory, setFoodCategory]       = useState("");
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

  const filteredCountries = COUNTRIES.filter(
    (c) =>
      c.label.toLowerCase().includes(countrySearch.toLowerCase()) ||
      c.value.toLowerCase().includes(countrySearch.toLowerCase()),
  );

  const validate = (): boolean => {
    const e: Record<string, string> = {};
    if (!productName.trim())  e.productName = "Product name is required";
    if (!selectedDomain)      e.domain      = "Select a domain";
    if (!selectedCountry)     e.country     = "Select a target country";
    if (selectedDomain === "MEDICAL_DEVICE" && !deviceClass)
      e.deviceClass = "Select a device class";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = () => {
    if (!validate()) return;
    const templates = templatesQ.data ?? [];
    // Match on domain + country, then domain only, then first available
    const match =
      templates.find(
        (t) =>
          t.domain.toUpperCase() === selectedDomain &&
          t.country.toLowerCase() === selectedCountry,
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
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#e2e8f0]">
          <div>
            <h2 className="text-base font-bold text-[#0f172a]">New Project</h2>
            <p className="text-[11px] text-[#94a3b8] mt-0.5">
              Set up a new regulatory filing project
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-[#0f172a] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Product name */}
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider mb-1.5">
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
                "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors",
                errors.productName ? "border-[#dc2626]" : "border-[#e2e8f0]",
              )}
            />
            {errors.productName && (
              <p className="text-[10px] text-[#dc2626] mt-1">{errors.productName}</p>
            )}
          </div>

          {/* Domain */}
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider mb-2">
              Domain *
            </label>
            <div className="grid grid-cols-2 gap-3">
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
                      "flex flex-col items-start p-4 rounded-xl border-2 text-left transition-all",
                      sel
                        ? "border-[#2563eb] bg-[#eff6ff]"
                        : "border-[#e2e8f0] hover:border-[#cbd5e1]",
                    )}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center mb-2"
                      style={{
                        background: `${d.color}15`,
                        border: `1px solid ${d.color}30`,
                      }}
                    >
                      <Icon size={16} style={{ color: d.color }} />
                    </div>
                    <p
                      className={cn(
                        "text-xs font-bold",
                        sel ? "text-[#2563eb]" : "text-[#0f172a]",
                      )}
                    >
                      {d.label}
                    </p>
                    <p className="text-[10px] text-[#94a3b8] mt-0.5">{d.desc}</p>
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
              <label className="block text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider mb-1.5">
                Device class *
              </label>
              <select
                value={deviceClass}
                onChange={(e) => {
                  setDeviceClass(e.target.value);
                  setErrors((p) => ({ ...p, deviceClass: "" }));
                }}
                className={cn(
                  "w-full px-3 py-2.5 bg-white border rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb]",
                  errors.deviceClass ? "border-[#dc2626]" : "border-[#e2e8f0]",
                )}
              >
                <option value="">Select device class</option>
                {DEVICE_CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              {errors.deviceClass && (
                <p className="text-[10px] text-[#dc2626] mt-1">{errors.deviceClass}</p>
              )}
            </div>
          )}

          {/* Conditional: Food category */}
          {selectedDomain === "FOOD" && (
            <div>
              <label className="block text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider mb-1.5">
                Food category
              </label>
              <input
                value={foodCategory}
                onChange={(e) => setFoodCategory(e.target.value)}
                placeholder="e.g. nutraceutical, beverage, dairy supplement"
                className="w-full px-3 py-2.5 bg-white border border-[#e2e8f0] rounded-xl text-sm text-[#0f172a] outline-none focus:border-[#2563eb] transition-colors"
              />
            </div>
          )}

          {/* Country */}
          <div>
            <label className="block text-[10px] font-mono text-[#94a3b8] uppercase tracking-wider mb-1.5">
              Target country *
            </label>
            <div
              className={cn(
                "border rounded-xl overflow-hidden",
                errors.country ? "border-[#dc2626]" : "border-[#e2e8f0]",
              )}
            >
              <div className="flex items-center gap-2 px-3 py-2 border-b border-[#e2e8f0] bg-[#f8fafc]">
                <Search size={12} className="text-[#94a3b8] flex-shrink-0" />
                <input
                  value={countrySearch}
                  onChange={(e) => setCountrySearch(e.target.value)}
                  placeholder="Search countries…"
                  className="flex-1 text-xs bg-transparent outline-none text-[#0f172a] placeholder-[#cbd5e1]"
                />
              </div>
              <div className="max-h-44 overflow-y-auto">
                {filteredCountries.map((c) => (
                  <button
                    key={c.value}
                    type="button"
                    onClick={() => {
                      setSelectedCountry(c.value);
                      setErrors((p) => ({ ...p, country: "" }));
                    }}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-3 py-2 text-left hover:bg-[#f8fafc] transition-colors text-xs",
                      selectedCountry === c.value
                        ? "bg-[#eff6ff] text-[#2563eb] font-semibold"
                        : "text-[#0f172a]",
                    )}
                  >
                    <span className="text-sm">{c.flag}</span>
                    <span>{c.label}</span>
                  </button>
                ))}
              </div>
            </div>
            {errors.country && (
              <p className="text-[10px] text-[#dc2626] mt-1">{errors.country}</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#e2e8f0] bg-[#f8fafc]">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#64748b] hover:text-[#0f172a] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={createMut.isPending || templatesQ.isLoading}
            className={cn(
              "flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-bold transition-all",
              createMut.isPending || templatesQ.isLoading
                ? "bg-[#e2e8f0] text-[#94a3b8] cursor-not-allowed"
                : "bg-[#2563eb] text-white hover:bg-[#1d4ed8] active:scale-[0.98]",
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
