import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import AppLayout from "@/components/layout/AppLayout";

// Pages — lazy-loaded for performance
import { lazy, Suspense } from "react";

const LoginPage         = lazy(() => import("@/pages/LoginPage"));
const DashboardPage     = lazy(() => import("@/pages/DashboardPage"));
const QueryPage         = lazy(() => import("@/pages/QueryPage"));
const GapAssessmentPage = lazy(() => import("@/pages/GapAssessmentPage"));
const DossierPage       = lazy(() => import("@/pages/DossierPage"));
const AlertsPage        = lazy(() => import("@/pages/AlertsPage"));
const IngredientSpecsPage = lazy(() => import("@/pages/IngredientSpecsPage"));
const AllowableLimitsPage = lazy(() => import("@/pages/AllowableLimitsPage"));
const LabelingPage      = lazy(() => import("@/pages/LabelingPage"));
const LicensingPage     = lazy(() => import("@/pages/LicensingPage"));
const ExplorerPage      = lazy(() => import("@/pages/ExplorerPage"));
const DocumentsPage     = lazy(() => import("@/pages/DocumentsPage"));
const AuditPage         = lazy(() => import("@/pages/AuditPage"));
const SettingsPage      = lazy(() => import("@/pages/SettingsPage"));
const BillingPage       = lazy(() => import("@/pages/BillingPage"));
const FilingWizardPage      = lazy(() => import("@/pages/FilingWizardPage"));
const DocumentEditorPage    = lazy(() => import("@/pages/DocumentEditorPage"));
const ComplianceReviewPage  = lazy(() => import("@/pages/ComplianceReviewPage"));
const AdminPanelPage        = lazy(() => import("@/pages/AdminPanelPage"));
const RegulatoryDatabasePage = lazy(() => import("@/pages/RegulatoryDatabasePage"));
const ProjectsPage          = lazy(() => import("@/pages/ProjectsPage"));
const ProjectDetailPage     = lazy(() => import("@/pages/ProjectDetailPage"));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: (failureCount, error: any) => {
        // Don't retry 4xx errors — they won't resolve on retry
        if (error?.response?.status >= 400 && error?.response?.status < 500) return false;
        return failureCount < 2;
      },
    },
    mutations: { retry: 0 },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

// Full-page loading spinner shown during lazy chunk load
function PageLoader() {
  return (
    <div className="flex items-center justify-center h-screen bg-[#0a0c10]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 bg-[#00d4aa] rounded-xl flex items-center justify-center font-mono font-bold text-black text-sm">
          R∧
        </div>
        <div className="w-5 h-5 border-2 border-[#00d4aa] border-t-transparent rounded-full animate-spin" />
      </div>
    </div>
  );
}

export default function App() {
  // Check for token expiry on app focus (web-specific — no Electron equivalent needed)
  const { token, logout } = useAuthStore();

  useEffect(() => {
    const checkExpiry = () => {
      if (!token) return;
      try {
        const payload = JSON.parse(atob(token.split(".")[1]));
        if (payload.exp && Date.now() / 1000 > payload.exp) {
          logout();
        }
      } catch {
        // Invalid token — clear it
        logout();
      }
    };

    window.addEventListener("focus", checkExpiry);
    checkExpiry(); // Check immediately on mount
    return () => window.removeEventListener("focus", checkExpiry);
  }, [token, logout]);

  return (
    <QueryClientProvider client={queryClient}>
      {/*
        BrowserRouter replaces HashRouter.
        Requires server to serve index.html for all routes:
          - Nginx: try_files $uri $uri/ /index.html;
          - Vite dev: handled automatically
      */}
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected — all wrapped in AppLayout */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard"           element={<DashboardPage />} />
              <Route path="query"               element={<QueryPage />} />
              <Route path="gap-assessment"      element={<GapAssessmentPage />} />
              <Route path="dossier"             element={<DossierPage />} />
              <Route path="alerts"              element={<AlertsPage />} />
              <Route path="ingredient-specs"    element={<IngredientSpecsPage />} />
              <Route path="allowable-limits"    element={<AllowableLimitsPage />} />
              <Route path="labeling"            element={<LabelingPage />} />
              <Route path="licensing"           element={<LicensingPage />} />
              <Route path="explorer"            element={<ExplorerPage />} />
              <Route path="documents"           element={<DocumentsPage />} />
              <Route path="audit"               element={<AuditPage />} />
              <Route path="settings"            element={<SettingsPage />} />
              <Route path="billing"             element={<BillingPage />} />
              <Route path="filing-wizard"       element={<FilingWizardPage />} />
              <Route path="document-editor"     element={<DocumentEditorPage />} />
              <Route path="compliance-review"   element={<ComplianceReviewPage />} />
              <Route path="admin"               element={<AdminPanelPage />} />
              <Route path="regulatory-database" element={<RegulatoryDatabasePage />} />
              <Route path="projects"            element={<ProjectsPage />} />
              <Route path="projects/:id"        element={<ProjectDetailPage />} />
            </Route>

            {/* 404 → home */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: "#181c24",
            color: "#e8ecf2",
            border: "1px solid #2a3040",
            fontSize: "13px",
          },
          success: { iconTheme: { primary: "#00d4aa", secondary: "#000" } },
          error:   { iconTheme: { primary: "#ff4757", secondary: "#000" } },
        }}
      />
    </QueryClientProvider>
  );
}
