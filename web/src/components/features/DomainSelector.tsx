import { ChevronDown } from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { DOMAINS, DOMAIN_MAP, cn } from "@/lib/utils";

interface Props {
  compact?: boolean;
}

export default function DomainSelector({ compact }: Props) {
  const { selectedDomain, setSelectedDomain } = useAppStore();
  const selected = selectedDomain ? DOMAIN_MAP[selectedDomain] : null;

  if (compact) {
    return (
      <div>
        <div className="text-[9px] font-mono text-[#4a5568] uppercase tracking-widest mb-1">Domain</div>
        <select
          value={selectedDomain || ""}
          onChange={(e) => setSelectedDomain(e.target.value || null)}
          className="w-full appearance-none px-2.5 py-1.5 rounded-lg bg-[#181c24] border border-[#2a3040] text-xs text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors cursor-pointer"
        >
          <option value="">All domains</option>
          {DOMAINS.map((d) => (
            <option key={d.value} value={d.value}>{d.label}</option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <div className="relative">
      <select
        value={selectedDomain || ""}
        onChange={(e) => setSelectedDomain(e.target.value || null)}
        className={cn(
          "appearance-none pl-3 pr-7 py-1.5 rounded-lg border text-xs outline-none transition-colors cursor-pointer",
          selected
            ? "border-opacity-50"
            : "bg-[#111318] border-[#2a3040] text-[#8892a4] hover:border-[#4a5568]"
        )}
        style={selected ? {
          background: selected.bg,
          borderColor: `${selected.color}50`,
          color: selected.color,
        } : {}}
      >
        <option value="">All domains</option>
        {DOMAINS.map((d) => (
          <option key={d.value} value={d.value}>{d.label}</option>
        ))}
      </select>
      <ChevronDown size={11} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-[#4a5568]" />
    </div>
  );
}
