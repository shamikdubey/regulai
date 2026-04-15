import { cn } from "@/lib/utils";

interface TrustBadgeProps {
  score: number;
  level: string;
  showScore?: boolean;
  className?: string;
}

const TRUST_CONFIG: Record<string, { dot: string; text: string; label: string }> = {
  VERIFIED:   { dot: "#10b981", text: "#047857", label: "Verified" },
  HIGH:       { dot: "#3b82f6", text: "#1d4ed8", label: "High Confidence" },
  MODERATE:   { dot: "#f59e0b", text: "#b45309", label: "Moderate" },
  LOW:        { dot: "#ef4444", text: "#dc2626", label: "Low Confidence" },
  UNVERIFIED: { dot: "#9ca3af", text: "#6b7280", label: "Unverified" },
};

export function trustLevelFromScore(score: number): string {
  if (score >= 90) return "VERIFIED";
  if (score >= 75) return "HIGH";
  if (score >= 50) return "MODERATE";
  if (score >= 25) return "LOW";
  return "UNVERIFIED";
}

export function confidenceToTrust(confidence: string): { score: number; level: string } {
  const upper = (confidence ?? "").toUpperCase();
  if (upper === "HIGH")   return { score: 85, level: "HIGH" };
  if (upper === "MEDIUM") return { score: 60, level: "MODERATE" };
  return { score: 35, level: "LOW" };
}

export default function TrustBadge({
  score,
  level,
  showScore = false,
  className,
}: TrustBadgeProps) {
  const key = (level ?? "").toUpperCase();
  const config = TRUST_CONFIG[key] ?? TRUST_CONFIG.UNVERIFIED;
  const tooltip = `Trust Score: ${score}/100 — based on regulatory accuracy and user feedback`;

  return (
    <span
      className={cn("inline-flex items-center gap-1 text-[10px] font-semibold", className)}
      title={tooltip}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0 inline-block"
        style={{ background: config.dot }}
      />
      <span style={{ color: config.text }}>
        {config.label}
        {showScore && ` · ${score}/100`}
      </span>
    </span>
  );
}
