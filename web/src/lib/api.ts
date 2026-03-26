/**
 * API Client — Web edition
 * No Electron dependencies. Pure browser fetch + axios.
 * Adds:
 *   - Automatic token refresh on 401
 *   - X-Request-ID header on every request
 *   - Streaming support for AI responses (SSE)
 *   - Rate limit response handling (429)
 */
import axios, { AxiosInstance, AxiosError } from "axios";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";

// In production this is relative (/api/v1) because Nginx proxies to backend.
// In dev, Vite proxies /api → localhost:8000.
const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "/api/v1";

let apiClient: AxiosInstance | null = null;

export function getApiClient(): AxiosInstance {
  if (!apiClient) {
    apiClient = axios.create({
      baseURL: API_BASE,
      timeout: 90_000,          // 90s — AI endpoints can take a while
      headers: { "Content-Type": "application/json" },
    });

    // ── Request interceptor ──────────────────────────────────────────────────
    apiClient.interceptors.request.use((config) => {
      const token = useAuthStore.getState().token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      // Attach unique request ID for server-side log correlation
      config.headers["X-Request-ID"] = crypto.randomUUID();
      return config;
    });

    // ── Response interceptor ─────────────────────────────────────────────────
    apiClient.interceptors.response.use(
      (res) => res,
      async (error: AxiosError<{ detail: string | { error: string; limit: number; used: number } }>) => {
        const status = error.response?.status;
        const detail = error.response?.data?.detail;

        if (status === 401) {
          useAuthStore.getState().logout();
          // Redirect to login — works with BrowserRouter
          window.location.href = "/login?reason=session_expired";
          return Promise.reject(error);
        }

        if (status === 403) {
          const msg = typeof detail === "string" ? detail : "Access denied";
          toast.error(msg);
          return Promise.reject(error);
        }

        if (status === 422) {
          // Validation errors — extract first message
          const errors = (error.response?.data as any)?.detail;
          const msg = Array.isArray(errors)
            ? errors.map((e: any) => `${e.loc?.slice(-1)[0]}: ${e.msg}`).join("; ")
            : "Validation error";
          toast.error(msg);
          return Promise.reject(error);
        }

        if (status === 429) {
          // Rate limit exceeded
          const limitDetail = typeof detail === "object" ? detail : null;
          const msg = limitDetail
            ? `Daily limit reached: ${(limitDetail as any).used}/${(limitDetail as any).limit} queries used.`
            : "Too many requests. Please slow down.";
          toast.error(msg, { duration: 6000 });
          return Promise.reject(error);
        }

        if (status && status >= 500) {
          toast.error("Server error. Our team has been notified.");
          return Promise.reject(error);
        }

        // Network errors
        if (!error.response) {
          toast.error("Network error. Check your connection.");
        }

        return Promise.reject(error);
      }
    );
  }
  return apiClient;
}

// Reset client (e.g. after logout)
export function resetApiClient(): void {
  apiClient = null;
}

// ── Streaming SSE client ────────────────────────────────────────────────────
/**
 * Open a Server-Sent Events stream for AI responses.
 * Used by QueryPage for real-time token streaming.
 *
 * @param endpoint  API path, e.g. "/query/stream"
 * @param body      Request body
 * @param onToken   Called with each token as it arrives
 * @param onDone    Called when stream completes
 * @param onError   Called on stream error
 */
export async function streamRequest(
  endpoint: string,
  body: Record<string, unknown>,
  onToken: (token: string) => void,
  onDone: (fullResponse: string) => void,
  onError: (error: string) => void,
): Promise<() => void> {
  const token = useAuthStore.getState().token;
  const url = `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "X-Request-ID": crypto.randomUUID(),
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Stream failed" }));
    onError(typeof err.detail === "string" ? err.detail : "Stream request failed");
    return () => {};
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError("Streaming not supported by server");
    return () => {};
  }

  const decoder = new TextDecoder();
  let fullText = "";
  let cancelled = false;

  const pump = async () => {
    try {
      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) {
          onDone(fullText);
          break;
        }
        const chunk = decoder.decode(value, { stream: true });
        // SSE format: "data: <token>\n\n"
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              onDone(fullText);
              return;
            }
            try {
              const parsed = JSON.parse(data);
              const tokenText = parsed.token || parsed.text || data;
              fullText += tokenText;
              onToken(tokenText);
            } catch {
              // Not JSON — treat as raw token
              fullText += data;
              onToken(data);
            }
          }
        }
      }
    } catch (err: any) {
      if (!cancelled) {
        onError(err.message || "Stream interrupted");
      }
    }
  };

  pump();

  // Return cancel function
  return () => {
    cancelled = true;
    reader.cancel();
  };
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  jurisdiction?: string;
  domain?: string;
}

export interface Citation {
  regulation_name: string;
  jurisdiction: string;
  section?: string;
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  citations: Citation[];
  confidence: number;
  caveats?: string[];
  next_steps?: string[];
  regulatory_bodies?: string[];
  jurisdiction?: string;
  domain?: string;
  latency_ms: number;
}

export interface AuditEntry {
  id: string;
  query: string;
  jurisdiction?: string;
  domain?: string;
  confidence?: number;
  latency_ms?: number;
  created_at: string;
  hmac_signature?: string;
}

export interface RegulatoryBody {
  id: string;
  acronym: string;
  name: string;
  jurisdiction: string;
  domains: string[];
  description?: string;
  website?: string;
  established_year?: number;
}

export interface Regulation {
  id: string;
  name: string;
  short_name?: string;
  jurisdiction: string;
  domain: string;
  year?: string;
  status: string;
  description?: string;
  source_url?: string;
}

export interface Document {
  id: string;
  filename: string;
  jurisdiction?: string;
  domain?: string;
  processing_status: string;
  chunk_count?: number;
  file_size_bytes: number;
  created_at: string;
}

export interface TenantInfo {
  id: string;
  name: string;
  slug: string;
  allowed_jurisdictions: string[];
  allowed_domains: string[];
  query_limit_per_day: number;
}

export interface GapAssessmentRequest {
  product_name: string;
  product_description: string;
  product_type: string;
  target_jurisdictions: string[];
  current_approvals?: string[];
  intended_claims?: string;
}

export interface GapItem {
  jurisdiction: string;
  gap: string;
  requirement: string;
  risk_level: "HIGH" | "MEDIUM" | "LOW";
  estimated_timeline: string;
  action_required: string;
}

export interface GapAssessmentResponse {
  product_name: string;
  overall_risk: string;
  gaps: GapItem[];
  summary: string;
  critical_path: string[];
  estimated_total_months: number;
}

export interface DossierRequest {
  product_name: string;
  product_type: string;
  jurisdiction: string;
  submission_type: string;
  product_description: string;
  active_ingredients?: string;
  indication_or_use?: string;
  manufacturing_site?: string;
  sections_requested?: string[];
}

export interface DossierSection {
  section_id: string;
  title: string;
  content: string;
  completeness: "DRAFT" | "NEEDS_DATA" | "COMPLETE";
  missing_data: string[];
}

export interface DossierResponse {
  product_name: string;
  jurisdiction: string;
  submission_type: string;
  sections: DossierSection[];
  cover_letter_draft: string;
  submission_checklist: string[];
}

export interface Alert {
  id: string;
  title: string;
  summary: string;
  jurisdiction: string;
  domain: string;
  change_type: string;
  severity: string;
  effective_date?: string;
  source_url?: string;
  regulatory_body?: string;
  action_required?: string;
  tags?: string[];
  published_at: string;
}

export interface AlertSubscription {
  jurisdictions: string[];
  domains: string[];
  severity_threshold: string;
  email_enabled: boolean;
}

// ── API methods ─────────────────────────────────────────────────────────────

export const api = {
  // Auth
  login: (email: string, password: string) =>
    getApiClient().post<{ access_token: string; token_type: string }>(
      "/auth/token",
      new URLSearchParams({ username: email, password }),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    ).then(r => r.data),

  getMe: () =>
    getApiClient().get<{ id: string; email: string; full_name: string; role: string; tenant_id: string }>(
      "/auth/me"
    ).then(r => r.data),

  register: (data: { email: string; password: string; full_name: string; tenant_name: string }) =>
    getApiClient().post("/auth/register", data).then(r => r.data),

  // Query
  query: (req: QueryRequest) =>
    getApiClient().post<QueryResponse>("/query", req).then(r => r.data),

  // Regulations
  getBodies: (params?: { jurisdiction?: string; domain?: string }) =>
    getApiClient().get<RegulatoryBody[]>("/regulations/bodies", { params }).then(r => r.data),

  getRegulations: (params?: { jurisdiction?: string; domain?: string }) =>
    getApiClient().get<Regulation[]>("/regulations/regulations", { params }).then(r => r.data),

  // Documents
  uploadDocument: (file: File, jurisdiction?: string, domain?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (jurisdiction) fd.append("jurisdiction", jurisdiction);
    if (domain) fd.append("domain", domain);
    return getApiClient().post<Document>("/documents/upload", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data);
  },

  getDocuments: () =>
    getApiClient().get<Document[]>("/documents/").then(r => r.data),

  getDocumentStatus: (id: string) =>
    getApiClient().get<Document>(`/documents/${id}/status`).then(r => r.data),

  // Audit
  getAuditLog: (params?: { limit?: number; offset?: number; jurisdiction?: string; domain?: string }) =>
    getApiClient().get<AuditEntry[]>("/audit/", { params }).then(r => r.data),

  getAuditEntry: (id: string) =>
    getApiClient().get<AuditEntry & { response: string; citations: Citation[] }>(`/audit/${id}`).then(r => r.data),

  // Tenant
  getMyTenant: () =>
    getApiClient().get<TenantInfo>("/tenants/me").then(r => r.data),

  // Gap Assessment
  runGapAssessment: (req: GapAssessmentRequest) =>
    getApiClient().post<GapAssessmentResponse>("/gap-assessment", req).then(r => r.data),

  // Dossier
  draftDossier: (req: DossierRequest) =>
    getApiClient().post<DossierResponse>("/dossier", req).then(r => r.data),

  // Alerts
  getAlerts: (params?: { jurisdiction?: string; domain?: string; severity?: string }) =>
    getApiClient().get<Alert[]>("/alerts", { params }).then(r => r.data),
  seedAlerts: () =>
    getApiClient().post("/alerts/seed").then(r => r.data),
  subscribeAlerts: (data: AlertSubscription) =>
    getApiClient().post("/alerts/subscribe", data).then(r => r.data),
  getAlertSubscription: () =>
    getApiClient().get("/alerts/subscription").then(r => r.data),

  // Ingredient Specs
  getIngredientSpecs: (params?: Record<string, string>) =>
    getApiClient().get("/ingredient-specs", { params }).then(r => r.data),
  seedIngredientSpecs: () =>
    getApiClient().post("/ingredient-specs/seed").then(r => r.data),

  // Allowable Limits
  getAllowableLimits: (params?: Record<string, string>) =>
    getApiClient().get("/allowable-limits", { params }).then(r => r.data),
  seedAllowableLimits: () =>
    getApiClient().post("/allowable-limits/seed").then(r => r.data),

  // Labeling
  getLabelingRequirements: (params?: Record<string, string>) =>
    getApiClient().get("/labeling-requirements", { params }).then(r => r.data),
  seedLabelingRequirements: () =>
    getApiClient().post("/labeling-requirements/seed").then(r => r.data),

  // Licensing
  getLicensingPathways: (params?: Record<string, string>) =>
    getApiClient().get("/licensing-pathways", { params }).then(r => r.data),
  seedLicensingPathways: () =>
    getApiClient().post("/licensing-pathways/seed").then(r => r.data),
};
