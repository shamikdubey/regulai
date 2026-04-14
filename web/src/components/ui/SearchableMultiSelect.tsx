import { useState, useMemo } from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchableMultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
}

export default function SearchableMultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Search…",
}: SearchableMultiSelectProps) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(
    () =>
      query.trim()
        ? options.filter((o) =>
            o.toLowerCase().includes(query.toLowerCase()),
          )
        : options,
    [options, query],
  );

  const toggle = (opt: string) => {
    if (selected.includes(opt)) {
      onChange(selected.filter((s) => s !== opt));
    } else {
      onChange([...selected, opt]);
    }
  };

  const selectAll = () => onChange([...options]);
  const clearAll  = () => onChange([]);

  return (
    <div className="border border-[#e2ede9] rounded-xl overflow-hidden bg-white">
      {/* Selected tags */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2.5 pb-1.5 border-b border-[#e2ede9]">
          {selected.map((s) => (
            <span
              key={s}
              className="flex items-center gap-1 px-2 py-0.5 bg-[#ecfdf5] border border-[#a7f3d0] text-[#047857] rounded-full text-[10px] font-semibold"
            >
              {s}
              <button
                type="button"
                onClick={() => toggle(s)}
                className="text-[#047857] hover:text-[#065f46] transition-colors"
                aria-label={`Remove ${s}`}
              >
                <X size={10} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#e2ede9] bg-[#f7faf9]">
        <Search size={12} className="text-[#9ca3af] flex-shrink-0" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          className="flex-1 text-xs bg-transparent outline-none text-[#111827] placeholder-[#9ca3af]"
        />
      </div>

      {/* Select all / Clear all */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#e2ede9] bg-white">
        <button
          type="button"
          onClick={selectAll}
          className="text-[10px] font-semibold text-[#047857] hover:text-[#065f46] transition-colors"
        >
          Select all
        </button>
        <span className="text-[10px] text-[#9ca3af]">
          {selected.length}/{options.length} selected
        </span>
        <button
          type="button"
          onClick={clearAll}
          className="text-[10px] font-semibold text-[#6b7280] hover:text-[#111827] transition-colors"
        >
          Clear all
        </button>
      </div>

      {/* Options list */}
      <div className="max-h-[200px] overflow-y-auto">
        {filtered.length === 0 ? (
          <p className="px-3 py-4 text-center text-xs text-[#9ca3af]">
            No options match "{query}"
          </p>
        ) : (
          filtered.map((opt) => {
            const checked = selected.includes(opt);
            return (
              <label
                key={opt}
                className={cn(
                  "flex items-center gap-2.5 px-3 py-2 cursor-pointer hover:bg-[#f0fdf4] transition-colors",
                  checked && "bg-[#ecfdf5]",
                )}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggle(opt)}
                  className="w-3.5 h-3.5 rounded accent-[#047857] flex-shrink-0"
                />
                <span
                  className={cn(
                    "text-xs",
                    checked ? "font-semibold text-[#047857]" : "text-[#374151]",
                  )}
                >
                  {opt}
                </span>
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}
