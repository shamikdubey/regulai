import { motion } from "framer-motion";
import { Loader2, CheckCircle2, XCircle, StopCircle } from "lucide-react";
import type { JobState } from "@/hooks/useJobPoller";
import { cn } from "@/lib/utils";

interface Props {
  job: JobState & { cancel: () => void };
  title: string;
  estimatedSeconds?: number;
}

export default function JobProgress({ job, title, estimatedSeconds = 60 }: Props) {
  if (!job.isRunning && !job.isDone) return null;

  const isPending  = job.status === "PENDING";
  const isProgress = job.status === "PROGRESS";
  const isSuccess  = job.status === "SUCCESS";
  const isFailure  = job.status === "FAILURE";

  return (
    <div className="bg-[#111318] border border-[#1f2530] rounded-2xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          {(isPending || isProgress) && (
            <Loader2 size={16} className="animate-spin text-[#00d4aa] flex-shrink-0" />
          )}
          {isSuccess && (
            <CheckCircle2 size={16} className="text-[#00d4aa] flex-shrink-0" />
          )}
          {isFailure && (
            <XCircle size={16} className="text-[#ff4757] flex-shrink-0" />
          )}
          <span className="text-sm font-bold text-[#e8ecf2]">{title}</span>
        </div>

        {(isPending || isProgress) && (
          <button
            onClick={job.cancel}
            className="flex items-center gap-1.5 text-[10px] text-[#4a5568] hover:text-[#ff4757] transition-colors"
          >
            <StopCircle size={11} /> Cancel
          </button>
        )}

        {isSuccess && (
          <span className="text-[10px] font-mono text-[#00d4aa]">Complete</span>
        )}
        {isFailure && (
          <span className="text-[10px] font-mono text-[#ff4757]">Failed</span>
        )}
      </div>

      {/* Progress bar */}
      {(isPending || isProgress) && (
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-[#8892a4]">
              {job.message || "Processing…"}
            </span>
            <span className="text-[10px] font-mono text-[#4a5568]">
              {job.percent}%
            </span>
          </div>
          <div className="h-1.5 bg-[#1f2530] rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-[#00d4aa] rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${Math.max(job.percent, isPending ? 3 : 5)}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </div>
          {estimatedSeconds > 0 && isPending && (
            <p className="text-[9px] text-[#4a5568] mt-1.5 font-mono">
              Estimated: ~{Math.ceil(estimatedSeconds / 60)} minute{estimatedSeconds > 60 ? "s" : ""}
            </p>
          )}
        </div>
      )}

      {/* Steps indicator */}
      {isProgress && job.step && (
        <div className="flex items-center gap-2 mt-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#00d4aa] animate-pulse" />
          <span className="text-[10px] font-mono text-[#4a5568] capitalize">
            {job.step.replace(/_/g, " ")}
          </span>
        </div>
      )}

      {/* Error message */}
      {isFailure && job.error && (
        <div className="mt-2 px-3 py-2 rounded-lg bg-[rgba(255,71,87,0.08)] border border-[rgba(255,71,87,0.2)]">
          <p className="text-xs text-[#ff9999]">{job.error}</p>
        </div>
      )}

      {/* Success summary */}
      {isSuccess && (
        <div className="mt-1 flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#00d4aa]" />
          <span className="text-[10px] text-[#00d4aa]">Results ready — scroll down to view</span>
        </div>
      )}
    </div>
  );
}
