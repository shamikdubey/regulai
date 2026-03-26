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
    <div className="min-h-screen bg-[#0a0c10] flex items-center justify-center p-6">
      <div aria-hidden className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-[#00d4aa] opacity-[0.03] rounded-full blur-3xl" />
      </div>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}
        className="w-full max-w-sm relative z-10">
        <div className="text-center mb-10">
          <div className="inline-flex w-14 h-14 bg-[#00d4aa] rounded-2xl items-center justify-center font-mono text-xl font-bold text-black mb-5">R∧</div>
          <h1 className="font-serif text-3xl font-normal text-[#e8ecf2] mb-1">RegulAI</h1>
          <p className="text-xs text-[#4a5568] font-mono tracking-[0.2em] uppercase">Compliance Intelligence</p>
        </div>
        <div className="bg-[#111318] border border-[#1f2530] rounded-2xl p-8">
          <h2 className="text-base font-bold mb-6 text-[#e8ecf2]">Sign in to your workspace</h2>
          {error && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }}
              className="flex items-center gap-2 px-3 py-2.5 rounded-lg bg-[rgba(255,71,87,0.08)] border border-[rgba(255,71,87,0.2)] mb-4">
              <AlertCircle size={13} className="text-[#ff4757] flex-shrink-0" />
              <p className="text-xs text-[#ff9999]">{error}</p>
            </motion.div>
          )}
          <form onSubmit={handleLogin} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="block text-[10px] font-mono text-[#4a5568] mb-1.5 uppercase tracking-wider">Work email</label>
              <input id="email" type="email" value={email} onChange={e => { setEmail(e.target.value); setError(""); }}
                placeholder="you@company.com" autoComplete="email" autoFocus
                className={cn("w-full px-3 py-2.5 bg-[#181c24] border rounded-xl text-sm text-[#e8ecf2] placeholder-[#4a5568] outline-none transition-all",
                  error ? "border-[rgba(255,71,87,0.5)]" : "border-[#2a3040] focus:border-[#00d4aa]")} />
            </div>
            <div>
              <label htmlFor="password" className="block text-[10px] font-mono text-[#4a5568] mb-1.5 uppercase tracking-wider">Password</label>
              <div className="relative">
                <input id="password" type={showPw ? "text" : "password"} value={password}
                  onChange={e => { setPassword(e.target.value); setError(""); }}
                  placeholder="••••••••" autoComplete="current-password"
                  className={cn("w-full px-3 py-2.5 pr-10 bg-[#181c24] border rounded-xl text-sm text-[#e8ecf2] placeholder-[#4a5568] outline-none transition-all",
                    error ? "border-[rgba(255,71,87,0.5)]" : "border-[#2a3040] focus:border-[#00d4aa]")} />
                <button type="button" onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#4a5568] hover:text-[#8892a4]" aria-label="Toggle password visibility">
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading}
              className={cn("w-full py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98]",
                loading ? "bg-[#1f2530] text-[#4a5568] cursor-not-allowed" : "bg-[#00d4aa] text-black hover:bg-[#00bfa5]")}>
              {loading ? <><Loader2 size={15} className="animate-spin" /> Signing in…</> : "Sign in"}
            </button>
          </form>
          <p className="text-center text-[11px] text-[#4a5568] mt-5">
            Need access?{" "}<a href="mailto:hello@regulai.app" className="text-[#6699ff] hover:underline">Contact your administrator</a>
          </p>
        </div>
        <p className="text-center text-[10px] text-[#2a3040] mt-6">
          GDPR compliant · Data encrypted at rest · ISO 27001
        </p>
      </motion.div>
    </div>
  );
}
