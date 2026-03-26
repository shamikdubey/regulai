import { useState, useRef, useEffect, useMemo } from "react";
import { Search, X, ChevronDown } from "lucide-react";
import { useAppStore } from "@/stores/appStore";
import { cn, JURISDICTIONS, JURISDICTION_MAP, TIER_COLORS } from "@/lib/utils";

interface Props { compact?: boolean; }

export default function JurisdictionSelector({ compact }: Props) {
  const { selectedJurisdiction, setSelectedJurisdiction } = useAppStore();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 50);
  }, [open]);

  type JItem = { value: string; label: string; flag: string; tier: number };
  const q = search.toLowerCase().trim();
  const filtered = useMemo(() =>
    q ? (JURISDICTIONS as JItem[]).filter((j: JItem) =>
      j.label.toLowerCase().includes(q) ||
      j.value.toLowerCase().includes(q)
    ) : (JURISDICTIONS as JItem[]),
    [q]
  );

  const selected = selectedJurisdiction ? JURISDICTION_MAP[selectedJurisdiction] : null;

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          "w-full flex items-center gap-2 rounded-lg border bg-[#181c24] border-[#2a3040] hover:border-[#4a5568] text-left transition-colors",
          compact ? "px-2 py-1.5" : "px-3 py-2"
        )}
      >
        {selected ? (
          <>
            <span className="text-base flex-shrink-0 leading-none">{selected.flag}</span>
            <span className={cn("flex-1 truncate text-[#e8ecf2]", compact ? "text-[10px]" : "text-xs")}>
              {selected.label}
            </span>
            <button
              onClick={e => { e.stopPropagation(); setSelectedJurisdiction(null); }}
              className="flex-shrink-0 text-[#4a5568] hover:text-[#ff4757] transition-colors"
            >
              <X size={10} />
            </button>
          </>
        ) : (
          <>
            <span className={cn("flex-1 text-[#4a5568]", compact ? "text-[10px]" : "text-xs")}>
              All {JURISDICTIONS.length} countries
            </span>
            <ChevronDown size={10} className="text-[#4a5568] flex-shrink-0" />
          </>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute top-full left-0 mt-1 bg-[#111318] border border-[#2a3040] rounded-xl shadow-2xl z-50 overflow-hidden"
          style={{ width: "280px" }}
        >
          {/* Search bar */}
          <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1f2530]">
            <Search size={11} className="text-[#4a5568] flex-shrink-0" />
            <input
              ref={inputRef}
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={`Search ${JURISDICTIONS.length} countries...`}
              className="flex-1 bg-transparent text-xs text-[#e8ecf2] placeholder-[#4a5568] outline-none"
            />
            {search && (
              <button onClick={() => setSearch("")} className="text-[#4a5568] hover:text-[#e8ecf2]">
                <X size={10} />
              </button>
            )}
            <span className="text-[9px] font-mono text-[#4a5568]">{filtered.length}</span>
          </div>

          {/* All option */}
          {!q && (
            <button
              onClick={() => { setSelectedJurisdiction(null); setOpen(false); }}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 text-xs border-b border-[#1f2530] transition-colors",
                !selectedJurisdiction
                  ? "bg-[rgba(0,212,170,0.08)] text-[#00d4aa]"
                  : "text-[#4a5568] hover:bg-[#181c24] hover:text-[#8892a4]"
              )}
            >
              <span className="text-base leading-none">🌍</span>
              <span className="flex-1">All jurisdictions</span>
              <span className="text-[9px] font-mono opacity-50">{JURISDICTIONS.length}</span>
            </button>
          )}

          {/* Flat country list */}
          <div className="overflow-y-auto" style={{ maxHeight: "360px" }}>
            {filtered.length === 0 ? (
              <div className="py-6 text-center text-[10px] text-[#4a5568] font-mono">
                No countries match "{search}"
              </div>
            ) : (
              filtered.map((country: JItem) => (
                <button
                  key={country.value}
                  onClick={() => {
                    setSelectedJurisdiction(
                      country.value === selectedJurisdiction ? null : country.value
                    );
                    setOpen(false);
                    setSearch("");
                  }}
                  className={cn(
                    "w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors border-b border-[#1f2530] border-opacity-40",
                    selectedJurisdiction === country.value
                      ? "bg-[rgba(0,212,170,0.08)] text-[#00d4aa]"
                      : "text-[#8892a4] hover:bg-[#181c24] hover:text-[#e8ecf2]"
                  )}
                >
                  <span className="text-base leading-none flex-shrink-0">{country.flag}</span>
                  <span className="flex-1 text-left">{country.label}</span>
                  <span
                    className="text-[8px] font-mono flex-shrink-0 opacity-50"
                    style={{ color: TIER_COLORS[country.tier] }}
                  >
                    T{country.tier}
                  </span>
                </button>
              ))
            )}
          </div>

          {/* Footer: tier legend */}
          <div className="px-3 py-1.5 border-t border-[#1f2530] flex items-center gap-4">
            {([1, 2, 3] as const).map(t => (
              <span key={t} className="flex items-center gap-1 text-[9px]">
                <span className="font-mono font-bold" style={{ color: TIER_COLORS[t] }}>T{t}</span>
                <span className="text-[#4a5568]">{t === 1 ? "Full" : t === 2 ? "Core" : "Basic"}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
