import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Loader2, AlertCircle } from "lucide-react";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { setToken, setUser, setTenant, isAuthenticated } = useAuthStore();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    if (isAuthenticated()) navigate("/dashboard", { replace: true });
  }, []);

  useEffect(() => {
    if (params.get("reason") === "session_expired") {
      toast.error("Your session expired. Please sign in again.");
    }
  }, [params]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) { setError("Please enter email and password."); return; }
    setError(""); setLoading(true);
    try {
      const tokenData = await api.login(email.trim().toLowerCase(), password);
      setToken(tokenData.access_token);
      const me = await api.getMe();
      setUser({ id: me.id, email: me.email, name: me.full_name || me.email, role: me.role, tenant_id: me.tenant_id });
      const tenantData = await api.getMyTenant();
      setTenant({ id: tenantData.id, name: tenantData.name, slug: tenantData.slug,
        allowedJurisdictions: tenantData.allowed_jurisdictions,
        allowedDomains: tenantData.allowed_domains, queryLimitPerDay: tenantData.query_limit_per_day });
      toast.success("Welcome back!");
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      const msg = err?.response?.data?.detail;
      setError(typeof msg === "string" ? (msg.includes("Incorrect") ? "Incorrect email or password." : msg) : "Sign in failed.");
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-[#f7faf9] flex items-center justify-center p-6">
      <div aria-hidden className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-[#047857] opacity-[0.04] rounded-full blur-3xl" />
      </div>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
        className="w-full max-w-sm relative z-10">
        <div className="text-center mb-10">
          <div className="inline-flex w-14 h-14 bg-[#047857] rounded-2xl items-center justify-center font-mono text-xl font-bold text-white mb-5">R∧</div>
          <h1 className="font-serif text-3xl font-normal text-[#111827] mb-1">RegulAI</h1>
          <p className="text-xs text-[#9ca3af] font-mono tracking-[0.2em] uppercase">Compliance Intelligence</p>
        </div>
        <div className="bg-white border border-[#e2ede9] rounded-2xl p-8 shadow-sm">
          <h2 className="text-base font-bold mb-6 text-[#111827]">Sign in to your workspace</h2>
          {error && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-[rgba(220,38,38,0.06)] border border-[rgba(220,38,38,0.2)] mb-4">
              <AlertCircle size={13} className="text-[#dc2626] flex-shrink-0" />
              <p className="text-xs text-[#dc2626]">{error}</p>
            </motion.div>
          )}
          <form onSubmit={handleLogin} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="block text-[10px] font-mono text-[#9ca3af] mb-1.5 uppercase tracking-wider">Work email</label>
              <input id="email" type="email" value={email} onChange={e => { setEmail(e.target.value); setError(""); }}
                placeholder="you@company.com" autoComplete="email" autoFocus
                className={cn("w-full px-3 py-2.5 bg-[#f7faf9] border rounded-xl text-sm text-[#111827] placeholder-[#cbd5e1] outline-none transition-all",
                  error ? "border-[rgba(220,38,38,0.4)]" : "border-[#e2ede9] focus:border-[#047857]")} />
            </div>
            <div>
              <label htmlFor="password" className="block text-[10px] font-mono text-[#9ca3af] mb-1.5 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input id="password" type={showPw ? "text" : "password"} value={password}
                  onChange={e => { setPassword(e.target.value); setError(""); }}
                  placeholder="••••••••" autoComplete="current-password"
                  className={cn("w-full px-3 py-2.5 pr-10 bg-[#f7faf9] border rounded-xl text-sm text-[#111827] placeholder-[#cbd5e1] outline-none transition-all",
                    error ? "border-[rgba(220,38,38,0.4)]" : "border-[#e2ede9] focus:border-[#047857]")} />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9ca3af] hover:text-[#6b7280]" aria-label="Toggle password visibility">
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading}
              className={cn("w-full py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98]",
                loading ? "bg-[#e2ede9] text-[#9ca3af] cursor-not-allowed" : "bg-[#047857] text-white hover:bg-[#065f46]")}>
              {loading ? <><Loader2 size={15} className="animate-spin" /> Signing in…</> : "Sign in"}
            </button>
          </form>
          <p className="text-center text-[11px] text-[#9ca3af] mt-5">
            Need access?{" "}<a href="mailto:hello@regulai.app" className="text-[#047857] hover:underline">Contact your administrator</a>
          </p>
        </div>
        <p className="text-center text-[10px] text-[#cbd5e1] mt-6">
          GDPR compliant · Data encrypted at rest · ISO 27001
        </p>
      </motion.div>
    </div>
  );
}
