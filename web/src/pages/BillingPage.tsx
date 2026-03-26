import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Check, Zap, TrendingUp, Building2, Loader2, ExternalLink, BarChart2 } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

type Plan = { slug:string;name:string;price_monthly_usd:number|null;query_limit_per_day:number;max_users:number;features:string[];trial_days:number };
type Usage = { plan:string;billing_status:string;usage:{queries_today:number;queries_limit_per_day:number;queries_today_pct:number;queries_this_month:number;documents:number;documents_limit:number;users:number;users_limit:number} };

const PLAN_ICONS: Record<string, any> = { starter: Zap, growth: TrendingUp, business: Building2, enterprise: Building2 };

export default function BillingPage() {
  const { user } = useAuthStore();
  const [checkoutLoading, setCheckoutLoading] = useState<string|null>(null);

  const plansQ = useQuery({ queryKey:["plans"], queryFn:()=>getApiClient().get<Record<string,Plan>>("/billing/plans").then(r=>r.data) });
  const usageQ = useQuery({ queryKey:["usage"], queryFn:()=>getApiClient().get<Usage>("/billing/usage").then(r=>r.data), refetchInterval: 60000 });
  const subQ = useQuery({ queryKey:["subscription"], queryFn:()=>getApiClient().get("/billing/subscription").then(r=>r.data) });

  const portalMut = useMutation({
    mutationFn: () => getApiClient().post<{portal_url:string}>("/billing/portal").then(r=>r.data),
    onSuccess: (d) => window.open(d.portal_url, "_blank"),
    onError: () => toast.error("Could not open billing portal"),
  });

  const handleCheckout = async (planSlug: string) => {
    setCheckoutLoading(planSlug);
    try {
      const resp = await getApiClient().post<{checkout_url:string}>("/billing/checkout", {
        plan: planSlug,
        success_url: `${window.location.origin}/billing?success=1`,
        cancel_url: `${window.location.origin}/billing`,
      });
      window.location.href = resp.data.checkout_url;
    } catch { toast.error("Checkout failed"); }
    finally { setCheckoutLoading(null); }
  };

  const usage = usageQ.data?.usage;
  const plans = plansQ.data ? Object.values(plansQ.data) : [];
  const currentPlan = subQ.data?.plan || "trial";

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-[#e8ecf2]">Billing & Plans</h1>
          <p className="text-xs text-[#4a5568] mt-1">Current plan: <span className="text-[#00d4aa] font-semibold capitalize">{currentPlan}</span></p>
        </div>
        {subQ.data?.stripe_subscription_id && (
          <button onClick={() => portalMut.mutate()} disabled={portalMut.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-xs text-[#8892a4] hover:text-[#e8ecf2] hover:border-[#4a5568] transition-all">
            {portalMut.isPending ? <Loader2 size={12} className="animate-spin"/> : <ExternalLink size={12}/>}
            Manage subscription
          </button>
        )}
      </div>

      {/* Usage dashboard */}
      {usage && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          {[
            { label: "Queries today", value: usage.queries_today, limit: usage.queries_limit_per_day, pct: usage.queries_today_pct },
            { label: "This month", value: usage.queries_this_month, limit: null, pct: null },
            { label: "Documents", value: usage.documents, limit: usage.documents_limit, pct: null },
            { label: "Users", value: usage.users, limit: usage.users_limit, pct: null },
          ].map(({ label, value, limit, pct }) => (
            <div key={label} className="bg-[#111318] border border-[#1f2530] rounded-xl p-4">
              <div className="text-[10px] text-[#4a5568] mb-2 font-mono uppercase tracking-wider">{label}</div>
              <div className="text-xl font-bold text-[#e8ecf2]">{value.toLocaleString()}</div>
              {limit && <div className="text-[10px] text-[#4a5568] mt-0.5">of {limit.toLocaleString()}</div>}
              {pct !== null && (
                <div className="mt-2 h-1 bg-[#1f2530] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${Math.min(pct, 100)}%`, background: pct > 90 ? "#ff4757" : pct > 70 ? "#f5a623" : "#00d4aa" }} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Plans */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {plans.map((plan) => {
          const Icon = PLAN_ICONS[plan.slug] || Zap;
          const isCurrent = plan.slug === currentPlan;
          const isEnterprise = plan.slug === "enterprise";

          return (
            <motion.div key={plan.slug} initial={{opacity:0,y:12}} animate={{opacity:1,y:0}}
              className={cn("bg-[#111318] border rounded-2xl p-5 flex flex-col relative transition-all",
                isCurrent ? "border-[#00d4aa] shadow-[0_0_20px_rgba(0,212,170,0.08)]" : "border-[#1f2530] hover:border-[#2a3040]")}>
              {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#00d4aa] text-black text-[9px] font-bold px-3 py-1 rounded-full">
                  CURRENT PLAN
                </div>
              )}
              {plan.trial_days > 0 && !isCurrent && plan.slug === "starter" && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#f5a623] text-black text-[9px] font-bold px-3 py-1 rounded-full">
                  14-DAY TRIAL
                </div>
              )}

              <div className="flex items-center gap-2 mb-3">
                <Icon size={16} className={isCurrent ? "text-[#00d4aa]" : "text-[#4a5568]"} />
                <span className="text-sm font-bold text-[#e8ecf2]">{plan.name}</span>
              </div>

              <div className="mb-4">
                {isEnterprise ? (
                  <div className="text-2xl font-bold text-[#e8ecf2]">Custom</div>
                ) : (
                  <>
                    <span className="text-2xl font-bold text-[#e8ecf2]">${plan.price_monthly_usd}</span>
                    <span className="text-xs text-[#4a5568]">/month</span>
                  </>
                )}
                <div className="text-[10px] text-[#4a5568] mt-1 font-mono">
                  {plan.query_limit_per_day.toLocaleString()} queries/day · {plan.max_users === 999999 ? "Unlimited" : plan.max_users} user{plan.max_users !== 1 ? "s" : ""}
                </div>
              </div>

              <ul className="space-y-1.5 flex-1 mb-5">
                {plan.features.map(f => (
                  <li key={f} className="flex items-start gap-2 text-xs text-[#8892a4]">
                    <Check size={11} className={cn("flex-shrink-0 mt-0.5", isCurrent ? "text-[#00d4aa]" : "text-[#4a5568]")} />
                    {f}
                  </li>
                ))}
              </ul>

              {!isCurrent && (
                isEnterprise ? (
                  <a href="mailto:sales@regulai.app"
                    className="w-full py-2 rounded-xl text-xs font-bold text-center border border-[#2a3040] text-[#8892a4] hover:border-[#4a5568] hover:text-[#e8ecf2] transition-all block">
                    Contact Sales
                  </a>
                ) : (
                  <button onClick={() => handleCheckout(plan.slug)} disabled={!!checkoutLoading}
                    className={cn("w-full py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition-all",
                      "bg-[#00d4aa] text-black hover:bg-[#00bfa5] active:scale-[0.98]",
                      checkoutLoading === plan.slug && "opacity-70 cursor-not-allowed")}>
                    {checkoutLoading === plan.slug ? <><Loader2 size={11} className="animate-spin"/>Loading…</> : "Upgrade"}
                  </button>
                )
              )}
              {isCurrent && (
                <div className="w-full py-2 rounded-xl text-xs font-bold text-center bg-[rgba(0,212,170,0.08)] text-[#00d4aa] border border-[rgba(0,212,170,0.2)]">
                  Active
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      <p className="text-center text-[11px] text-[#4a5568] mt-8">
        All plans include a 14-day free trial. No credit card required to start.
        Cancel anytime. <a href="mailto:support@regulai.app" className="text-[#6699ff] hover:underline">Contact us</a> for enterprise or annual pricing.
      </p>
    </div>
  );
}
