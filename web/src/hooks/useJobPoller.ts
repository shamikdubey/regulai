/**
 * useJobPoller — polls a background Celery job until it completes
 *
 * Usage:
 *   const { status, percent, message, result, error, cancel } = useJobPoller(jobId);
 *
 * States: idle → pending → progress → success | failure
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { getApiClient } from "@/lib/api";

export type JobStatus = "idle" | "PENDING" | "PROGRESS" | "SUCCESS" | "FAILURE";

export interface JobState<T = any> {
  status: JobStatus;
  percent: number;
  step: string;
  message: string;
  result: T | null;
  error: string | null;
  isRunning: boolean;
  isDone: boolean;
}

const POLL_INTERVAL_MS = 1500;   // 1.5s polling interval
const MAX_POLLS = 200;           // 200 × 1.5s = 5 min max

export function useJobPoller<T = any>(jobId: string | null): JobState<T> & { cancel: () => void } {
  const [state, setState] = useState<JobState<T>>({
    status: "idle",
    percent: 0,
    step: "",
    message: "",
    result: null,
    error: null,
    isRunning: false,
    isDone: false,
  });

  const pollCount = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    if (timerRef.current) clearTimeout(timerRef.current);
    setState(s => ({ ...s, status: "FAILURE", error: "Cancelled", isRunning: false, isDone: true }));
  }, []);

  useEffect(() => {
    if (!jobId) return;
    cancelledRef.current = false;
    pollCount.current = 0;

    setState({
      status: "PENDING",
      percent: 0,
      step: "queued",
      message: "Job queued…",
      result: null,
      error: null,
      isRunning: true,
      isDone: false,
    });

    const poll = async () => {
      if (cancelledRef.current) return;
      pollCount.current++;

      if (pollCount.current > MAX_POLLS) {
        setState(s => ({
          ...s,
          status: "FAILURE",
          error: "Job timed out after 5 minutes",
          isRunning: false,
          isDone: true,
        }));
        return;
      }

      try {
        const api = getApiClient();
        const resp = await api.get(`/jobs/${jobId}`);
        const data = resp.data;

        if (cancelledRef.current) return;

        if (data.status === "SUCCESS") {
          setState({
            status: "SUCCESS",
            percent: 100,
            step: "complete",
            message: "Complete",
            result: data.result,
            error: null,
            isRunning: false,
            isDone: true,
          });
          return;
        }

        if (data.status === "FAILURE") {
          setState({
            status: "FAILURE",
            percent: 0,
            step: "failed",
            message: "Failed",
            result: null,
            error: data.error || "Job failed",
            isRunning: false,
            isDone: true,
          });
          return;
        }

        // PENDING or PROGRESS — update and schedule next poll
        setState({
          status: data.status as JobStatus,
          percent: data.percent || 0,
          step: data.step || "",
          message: data.message || "Processing…",
          result: null,
          error: null,
          isRunning: true,
          isDone: false,
        });

        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err: any) {
        if (cancelledRef.current) return;
        // Network error — retry a few times before giving up
        if (pollCount.current < 5) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS * 2);
        } else {
          setState(s => ({
            ...s,
            status: "FAILURE",
            error: "Lost connection to server",
            isRunning: false,
            isDone: true,
          }));
        }
      }
    };

    // Start polling after a brief delay
    timerRef.current = setTimeout(poll, 500);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId]);

  return { ...state, cancel };
}
