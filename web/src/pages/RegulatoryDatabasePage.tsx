import { useState } from "react";
import { Database, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import IngredientSpecsPage from "./IngredientSpecsPage";
import AllowableLimitsPage from "./AllowableLimitsPage";
import LabelingPage from "./LabelingPage";
import LicensingPage from "./LicensingPage";

const TABS = [
  { id: "specs",     label: "Ingredient Specs" },
  { id: "limits",    label: "Allowable Limits" },
  { id: "labeling",  label: "Labeling Rules" },
  { id: "licensing", label: "Licensing" },
];

const TAB_INFO: Record<string, { title: string; description: string; whenToUse: string }> = {
  specs: {
    title: "Pharmacopoeial Standards",
    description:
      "Look up official quality standards (USP, EP, BP, JECFA) for ingredients and APIs. " +
      "Use this to verify your ingredient meets the required purity, potency and testing " +
      "specifications for your target market.",
    whenToUse:
      "Before formulation — check if your ingredient has a pharmacopoeial monograph in your target country.",
  },
  limits: {
    title: "Permitted Levels & MRLs",
    description:
      "Check maximum permitted levels for food additives, contaminants, pesticide residues " +
      "and nutrient reference values across 110 countries. Use this to verify your formulation " +
      "is within legal limits.",
    whenToUse:
      "During formulation review — ensure additive levels comply with local regulations.",
  },
  labeling: {
    title: "Label Requirements by Country",
    description:
      "Find mandatory label fields, allergen declarations, nutrition information panel formats, " +
      "warning seal requirements and language rules for each country. Use this when designing " +
      "your product label.",
    whenToUse:
      "Before packaging design — check what must appear on labels in each target market.",
  },
  licensing: {
    title: "Market Entry & Licensing Pathways",
    description:
      "Step-by-step licensing procedures, required documents, government fees and realistic " +
      "timelines for each country and product domain. Use this to plan your regulatory " +
      "strategy and budget.",
    whenToUse:
      "During market entry planning — understand the full licensing journey before committing resources.",
  },
};

export default function RegulatoryDatabasePage() {
  const [activeTab, setActiveTab] = useState("specs");
  const info = TAB_INFO[activeTab];

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-6 py-4 border-b border-[#e2ede9] bg-white flex items-center gap-3 flex-shrink-0">
        <Database size={18} className="text-[#047857]" />
        <div>
          <h1 className="text-sm font-bold text-[#111827]">Regulatory Database</h1>
          <p className="text-[10px] text-[#9ca3af] mt-0.5">
            Unified search across ingredient specs, allowable limits, labeling rules, and licensing pathways
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[#e2ede9] bg-white flex-shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-5 py-3 text-xs font-semibold border-b-2 transition-colors",
              activeTab === tab.id
                ? "text-[#047857] border-[#047857]"
                : "text-[#6b7280] border-transparent hover:text-[#111827] hover:border-[#e2ede9]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Context card — updates per active tab */}
      {info && (
        <div className="px-4 py-3 border-b border-[#e2ede9] bg-white flex-shrink-0">
          <div className="flex items-start gap-3 max-w-4xl">
            <div className="w-7 h-7 rounded-lg bg-[#ecfdf5] border border-[#a7f3d0] flex items-center justify-center flex-shrink-0 mt-0.5">
              <Info size={13} className="text-[#047857]" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-[#111827]">{info.title}</p>
              <p className="text-[11px] text-[#6b7280] mt-0.5 leading-relaxed">
                {info.description}
              </p>
              <p className="text-[10px] text-[#047857] font-semibold mt-1">
                When to use: {info.whenToUse}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab content — all tabs stay mounted so React Query cache is preserved on switch */}
      <div className="flex-1 overflow-hidden">
        <div style={{ display: activeTab === "specs" ? "flex" : "none" }} className="h-full light-override">
          <IngredientSpecsPage />
        </div>
        <div style={{ display: activeTab === "limits" ? "flex" : "none" }} className="h-full light-override">
          <AllowableLimitsPage />
        </div>
        <div style={{ display: activeTab === "labeling" ? "flex" : "none" }} className="h-full light-override">
          <LabelingPage />
        </div>
        <div style={{ display: activeTab === "licensing" ? "flex" : "none" }} className="h-full light-override">
          <LicensingPage />
        </div>
      </div>
    </div>
  );
}
