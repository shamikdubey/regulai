import { useState } from "react";
import { Database } from "lucide-react";
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

export default function RegulatoryDatabasePage() {
  const [activeTab, setActiveTab] = useState("specs");

  return (
    <div className="flex flex-col h-full">
      {/* Page header */}
      <div className="px-6 py-4 border-b border-[#e2e8f0] bg-white flex items-center gap-3 flex-shrink-0">
        <Database size={18} className="text-[#2563eb]" />
        <div>
          <h1 className="text-sm font-bold text-[#0f172a]">Regulatory Database</h1>
          <p className="text-[10px] text-[#94a3b8] mt-0.5">
            Unified search across ingredient specs, allowable limits, labeling rules, and licensing pathways
          </p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-[#e2e8f0] bg-white flex-shrink-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-5 py-3 text-xs font-semibold border-b-2 transition-colors",
              activeTab === tab.id
                ? "text-[#2563eb] border-[#2563eb]"
                : "text-[#64748b] border-transparent hover:text-[#0f172a] hover:border-[#e2e8f0]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

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
