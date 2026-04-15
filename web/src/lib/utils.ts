import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Region definitions ────────────────────────────────────────────────────────
export const REGIONS = [
  {
    id: "south_asia",
    label: "South Asia",
    color: "#ff6b35",
    countries: [
      { value: "india",       label: "India",       flag: "🇮🇳", tier: 1 },
      { value: "pakistan",    label: "Pakistan",    flag: "🇵🇰", tier: 2 },
      { value: "bangladesh",  label: "Bangladesh",  flag: "🇧🇩", tier: 2 },
      { value: "sri_lanka",   label: "Sri Lanka",   flag: "🇱🇰", tier: 2 },
      { value: "nepal",       label: "Nepal",       flag: "🇳🇵", tier: 2 },
      { value: "bhutan",      label: "Bhutan",      flag: "🇧🇹", tier: 3 },
      { value: "maldives",    label: "Maldives",    flag: "🇲🇻", tier: 3 },
      { value: "afghanistan", label: "Afghanistan", flag: "🇦🇫", tier: 3 },
    ],
  },
  {
    id: "east_asia",
    label: "East Asia",
    color: "#00d4aa",
    countries: [
      { value: "china",       label: "China",       flag: "🇨🇳", tier: 1 },
      { value: "japan",       label: "Japan",       flag: "🇯🇵", tier: 1 },
      { value: "south_korea", label: "South Korea", flag: "🇰🇷", tier: 2 },
      { value: "taiwan",      label: "Taiwan",      flag: "🇹🇼", tier: 2 },
      { value: "hong_kong",   label: "Hong Kong",   flag: "🇭🇰", tier: 2 },
      { value: "mongolia",    label: "Mongolia",    flag: "🇲🇳", tier: 3 },
      { value: "macau",       label: "Macau",       flag: "🇲🇴", tier: 3 },
    ],
  },
  {
    id: "southeast_asia",
    label: "Southeast Asia",
    color: "#6699ff",
    countries: [
      { value: "singapore",   label: "Singapore",   flag: "🇸🇬", tier: 1 },
      { value: "indonesia",   label: "Indonesia",   flag: "🇮🇩", tier: 2 },
      { value: "thailand",    label: "Thailand",    flag: "🇹🇭", tier: 2 },
      { value: "malaysia",    label: "Malaysia",    flag: "🇲🇾", tier: 2 },
      { value: "philippines", label: "Philippines", flag: "🇵🇭", tier: 2 },
      { value: "vietnam",     label: "Vietnam",     flag: "🇻🇳", tier: 2 },
      { value: "myanmar",     label: "Myanmar",     flag: "🇲🇲", tier: 3 },
      { value: "cambodia",    label: "Cambodia",    flag: "🇰🇭", tier: 3 },
      { value: "laos",        label: "Laos",        flag: "🇱🇦", tier: 3 },
      { value: "brunei",      label: "Brunei",      flag: "🇧🇳", tier: 3 },
    ],
  },
  {
    id: "oceania",
    label: "Oceania",
    color: "#00d4aa",
    countries: [
      { value: "australia",        label: "Australia",         flag: "🇦🇺", tier: 1 },
      { value: "new_zealand",      label: "New Zealand",       flag: "🇳🇿", tier: 2 },
      { value: "papua_new_guinea", label: "Papua New Guinea",  flag: "🇵🇬", tier: 3 },
      { value: "fiji",             label: "Fiji",              flag: "🇫🇯", tier: 3 },
    ],
  },
  {
    id: "north_america",
    label: "North America",
    color: "#f5a623",
    countries: [
      { value: "usa",                label: "United States",     flag: "🇺🇸", tier: 1 },
      { value: "canada",             label: "Canada",            flag: "🇨🇦", tier: 1 },
      { value: "mexico",             label: "Mexico",            flag: "🇲🇽", tier: 2 },
      { value: "guatemala",          label: "Guatemala",         flag: "🇬🇹", tier: 3 },
      { value: "costa_rica",         label: "Costa Rica",        flag: "🇨🇷", tier: 3 },
      { value: "panama",             label: "Panama",            flag: "🇵🇦", tier: 3 },
      { value: "cuba",               label: "Cuba",              flag: "🇨🇺", tier: 3 },
      { value: "dominican_republic", label: "Dominican Rep.",    flag: "🇩🇴", tier: 3 },
      { value: "honduras",           label: "Honduras",          flag: "🇭🇳", tier: 3 },
      { value: "el_salvador",        label: "El Salvador",       flag: "🇸🇻", tier: 3 },
      { value: "nicaragua",          label: "Nicaragua",         flag: "🇳🇮", tier: 3 },
    ],
  },
  {
    id: "latin_america",
    label: "Latin America",
    color: "#a78bfa",
    countries: [
      { value: "brazil",    label: "Brazil",    flag: "🇧🇷", tier: 1 },
      { value: "argentina", label: "Argentina", flag: "🇦🇷", tier: 2 },
      { value: "colombia",  label: "Colombia",  flag: "🇨🇴", tier: 2 },
      { value: "chile",     label: "Chile",     flag: "🇨🇱", tier: 2 },
      { value: "peru",      label: "Peru",      flag: "🇵🇪", tier: 2 },
      { value: "venezuela", label: "Venezuela", flag: "🇻🇪", tier: 3 },
      { value: "ecuador",   label: "Ecuador",   flag: "🇪🇨", tier: 3 },
      { value: "bolivia",   label: "Bolivia",   flag: "🇧🇴", tier: 3 },
      { value: "paraguay",  label: "Paraguay",  flag: "🇵🇾", tier: 3 },
      { value: "uruguay",   label: "Uruguay",   flag: "🇺🇾", tier: 3 },
    ],
  },
  {
    id: "western_europe",
    label: "Western Europe",
    color: "#6699ff",
    countries: [
      { value: "eu",            label: "European Union",  flag: "🇪🇺", tier: 1 },
      { value: "uk",            label: "United Kingdom",  flag: "🇬🇧", tier: 1 },
      { value: "switzerland",   label: "Switzerland",     flag: "🇨🇭", tier: 2 },
      { value: "norway",        label: "Norway",          flag: "🇳🇴", tier: 2 },
      { value: "iceland",       label: "Iceland",         flag: "🇮🇸", tier: 3 },
      { value: "liechtenstein", label: "Liechtenstein",   flag: "🇱🇮", tier: 3 },
    ],
  },
  {
    id: "eastern_europe",
    label: "Eastern Europe & CIS",
    color: "#8892a4",
    countries: [
      { value: "russia",         label: "Russia",         flag: "🇷🇺", tier: 2 },
      { value: "ukraine",        label: "Ukraine",        flag: "🇺🇦", tier: 2 },
      { value: "poland",         label: "Poland",         flag: "🇵🇱", tier: 2 },
      { value: "czech_republic", label: "Czech Republic", flag: "🇨🇿", tier: 2 },
      { value: "hungary",        label: "Hungary",        flag: "🇭🇺", tier: 2 },
      { value: "romania",        label: "Romania",        flag: "🇷🇴", tier: 2 },
      { value: "kazakhstan",     label: "Kazakhstan",     flag: "🇰🇿", tier: 2 },
      { value: "uzbekistan",     label: "Uzbekistan",     flag: "🇺🇿", tier: 3 },
      { value: "serbia",         label: "Serbia",         flag: "🇷🇸", tier: 3 },
      { value: "bulgaria",       label: "Bulgaria",       flag: "🇧🇬", tier: 3 },
      { value: "croatia",        label: "Croatia",        flag: "🇭🇷", tier: 3 },
      { value: "belarus",        label: "Belarus",        flag: "🇧🇾", tier: 3 },
      { value: "azerbaijan",     label: "Azerbaijan",     flag: "🇦🇿", tier: 3 },
      { value: "georgia",        label: "Georgia",        flag: "🇬🇪", tier: 3 },
      { value: "armenia",        label: "Armenia",        flag: "🇦🇲", tier: 3 },
      { value: "moldova",        label: "Moldova",        flag: "🇲🇩", tier: 3 },
    ],
  },
  {
    id: "middle_east",
    label: "Middle East",
    color: "#f5a623",
    countries: [
      { value: "uae",          label: "UAE",          flag: "🇦🇪", tier: 2 },
      { value: "saudi_arabia", label: "Saudi Arabia", flag: "🇸🇦", tier: 2 },
      { value: "turkey",       label: "Turkey",       flag: "🇹🇷", tier: 2 },
      { value: "israel",       label: "Israel",       flag: "🇮🇱", tier: 2 },
      { value: "egypt",        label: "Egypt",        flag: "🇪🇬", tier: 2 },
      { value: "iran",         label: "Iran",         flag: "🇮🇷", tier: 3 },
      { value: "jordan",       label: "Jordan",       flag: "🇯🇴", tier: 3 },
      { value: "kuwait",       label: "Kuwait",       flag: "🇰🇼", tier: 3 },
      { value: "qatar",        label: "Qatar",        flag: "🇶🇦", tier: 3 },
      { value: "bahrain",      label: "Bahrain",      flag: "🇧🇭", tier: 3 },
      { value: "oman",         label: "Oman",         flag: "🇴🇲", tier: 3 },
      { value: "lebanon",      label: "Lebanon",      flag: "🇱🇧", tier: 3 },
      { value: "iraq",         label: "Iraq",         flag: "🇮🇶", tier: 3 },
    ],
  },
  {
    id: "africa",
    label: "Africa",
    color: "#ff4757",
    countries: [
      { value: "south_africa",   label: "South Africa",   flag: "🇿🇦", tier: 2 },
      { value: "nigeria",        label: "Nigeria",        flag: "🇳🇬", tier: 2 },
      { value: "kenya",          label: "Kenya",          flag: "🇰🇪", tier: 2 },
      { value: "ghana",          label: "Ghana",          flag: "🇬🇭", tier: 2 },
      { value: "ethiopia",       label: "Ethiopia",       flag: "🇪🇹", tier: 3 },
      { value: "tanzania",       label: "Tanzania",       flag: "🇹🇿", tier: 3 },
      { value: "morocco",        label: "Morocco",        flag: "🇲🇦", tier: 3 },
      { value: "algeria",        label: "Algeria",        flag: "🇩🇿", tier: 3 },
      { value: "tunisia",        label: "Tunisia",        flag: "🇹🇳", tier: 3 },
      { value: "ivory_coast",    label: "Ivory Coast",    flag: "🇨🇮", tier: 3 },
      { value: "senegal",        label: "Senegal",        flag: "🇸🇳", tier: 3 },
      { value: "cameroon",       label: "Cameroon",       flag: "🇨🇲", tier: 3 },
      { value: "zimbabwe",       label: "Zimbabwe",       flag: "🇿🇼", tier: 3 },
      { value: "uganda",         label: "Uganda",         flag: "🇺🇬", tier: 3 },
      { value: "rwanda",         label: "Rwanda",         flag: "🇷🇼", tier: 3 },
      { value: "zambia",         label: "Zambia",         flag: "🇿🇲", tier: 3 },
      { value: "mozambique",     label: "Mozambique",     flag: "🇲🇿", tier: 3 },
      { value: "angola",         label: "Angola",         flag: "🇦🇴", tier: 3 },
      { value: "mauritius",      label: "Mauritius",      flag: "🇲🇺", tier: 3 },
      { value: "botswana",       label: "Botswana",       flag: "🇧🇼", tier: 3 },
      { value: "namibia",        label: "Namibia",        flag: "🇳🇦", tier: 3 },
      { value: "sudan",          label: "Sudan",          flag: "🇸🇩", tier: 3 },
      { value: "libya",          label: "Libya",          flag: "🇱🇾", tier: 3 },
      { value: "madagascar",     label: "Madagascar",     flag: "🇲🇬", tier: 3 },
    ],
  },
] as const;

// ── Flat arrays for backward compatibility ────────────────────────────────────
export const JURISDICTIONS = REGIONS.flatMap(r => r.countries as ReadonlyArray<{value: string; label: string; flag: string; tier: number}>);

export const DOMAINS = [
  { value: "food",     label: "Food Safety",      color: "#f5a623", bg: "rgba(245,166,35,0.12)" },
  { value: "pharma",   label: "Pharmaceuticals",  color: "#00d4aa", bg: "rgba(0,212,170,0.1)" },
  { value: "device",   label: "Medical Devices",  color: "#6699ff", bg: "rgba(102,153,255,0.1)" },
  { value: "nutra",    label: "Nutraceuticals",   color: "#a78bfa", bg: "rgba(167,139,250,0.1)" },
  { value: "ayurveda", label: "Ayurveda/TM",      color: "#ff6b35", bg: "rgba(255,107,53,0.12)" },
] as const;

export const DOMAIN_MAP = Object.fromEntries(DOMAINS.map((d) => [d.value, d]));
export const JURISDICTION_MAP = Object.fromEntries(JURISDICTIONS.map((j) => [j.value, j]));
export const REGION_MAP = Object.fromEntries(REGIONS.map((r) => [r.id, r]));

// Tier labels
export const TIER_LABELS: Record<number, string> = {
  1: "Full coverage",
  2: "Core coverage",
  3: "Authority & licensing",
};

export const TIER_COLORS: Record<number, string> = {
  1: "#00d4aa",
  2: "#f5a623",
  3: "#8892a4",
};

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function confidenceLabel(score: number): { label: string; color: string } {
  if (score >= 0.8) return { label: "High", color: "#00d4aa" };
  if (score >= 0.6) return { label: "Medium", color: "#f5a623" };
  return { label: "Low", color: "#ff4757" };
}
