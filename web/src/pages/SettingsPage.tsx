import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Key, Trash2, Plus, Copy, Eye, EyeOff, Shield, Monitor, LogOut, Check, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

const api = () => getApiClient();
type ApiKey = { id:string;name:string;prefix:string;scopes:string[];created_at:string;expires_at:string|null;last_used_at:string|null;is_active:boolean };
type Session = { id:string;device:string;ip:string;created_at:string;expires_at:string;last_used_at:string|null };
const SCOPES = [
  { value:"query:read",label:"AI Query",desc:"Run regulatory queries" },
  { value:"docs:write",label:"Upload Docs",desc:"Upload & manage documents" },
  { value:"audit:read",label:"Audit Log",desc:"Read audit entries" },
  { value:"data:read",label:"Reference Data",desc:"Read reference data" },
  { value:"*",label:"Full Access",desc:"All permissions" },
];
const TABS = [
  { id:"security",label:"Security",icon:Shield },
  { id:"apikeys",label:"API Keys",icon:Key },
  { id:"sessions",label:"Sessions",icon:Monitor },
] as const;

export default function SettingsPage() {
  const { user, tenant } = useAuthStore();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"security"|"apikeys"|"sessions">("security");
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyScopes, setNewKeyScopes] = useState(["query:read"]);
  const [newKeyExpiry, setNewKeyExpiry] = useState<number|null>(null);
  const [revealedKey, setRevealedKey] = useState<string|null>(null);
  const [showReveal, setShowReveal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [currentPw, setCurrentPw] = useState(""); const [newPw, setNewPw] = useState(""); const [confirmPw, setConfirmPw] = useState("");

  const keysQ = useQuery({ queryKey:["api-keys"], queryFn:()=>api().get<ApiKey[]>("/auth/api-keys").then(r=>r.data) });
  const sessQ = useQuery({ queryKey:["sessions"], queryFn:()=>api().get<Session[]>("/auth/sessions").then(r=>r.data) });
  const createKey = useMutation({
    mutationFn:(b:{name:string;scopes:string[];expires_days?:number})=>api().post<ApiKey&{key:string}>("/auth/api-keys",b).then(r=>r.data),
    onSuccess:(d)=>{ setRevealedKey(d.key); setNewKeyName(""); qc.invalidateQueries({queryKey:["api-keys"]}); toast.success("API key created — copy it now!"); },
    onError:()=>toast.error("Failed to create key"),
  });
  const revokeKey = useMutation({ mutationFn:(id:string)=>api().delete(`/auth/api-keys/${id}`), onSuccess:()=>{ qc.invalidateQueries({queryKey:["api-keys"]}); toast.success("Key revoked"); } });
  const revokeSession = useMutation({ mutationFn:(id:string)=>api().delete(`/auth/sessions/${id}`), onSuccess:()=>{ qc.invalidateQueries({queryKey:["sessions"]}); toast.success("Session revoked"); } });

  const copyKey = async () => { if (!revealedKey) return; await navigator.clipboard.writeText(revealedKey); setCopied(true); setTimeout(()=>setCopied(false),2000); };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6"><h1 className="text-xl font-bold text-[#e8ecf2]">Settings</h1><p className="text-xs text-[#4a5568] mt-1">{tenant?.name} · {user?.email}</p></div>
      <div className="flex gap-0 mb-6 border-b border-[#1f2530]">
        {TABS.map(({id,label,icon:Icon})=>(
          <button key={id} onClick={()=>setTab(id as any)}
            className={cn("flex items-center gap-1.5 px-4 py-2.5 text-xs font-semibold border-b-2 transition-all -mb-px",
              tab===id?"border-[#00d4aa] text-[#00d4aa]":"border-transparent text-[#4a5568] hover:text-[#8892a4]")}>
            <Icon size={12}/>{label}
          </button>
        ))}
      </div>

      {tab==="security" && (
        <div className="space-y-4">
          <div className="bg-[#111318] border border-[#1f2530] rounded-xl p-5">
            <h2 className="text-sm font-bold text-[#e8ecf2] mb-4">Change password</h2>
            <div className="space-y-3 max-w-sm">
              {[{l:"Current password",v:currentPw,s:setCurrentPw},{l:"New password",v:newPw,s:setNewPw},{l:"Confirm new password",v:confirmPw,s:setConfirmPw}].map(({l,v,s})=>(
                <div key={l}><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">{l}</label>
                  <input type="password" value={v} onChange={e=>s(e.target.value)} className="w-full px-3 py-2 bg-[#181c24] border border-[#2a3040] rounded-lg text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"/></div>
              ))}
              <button onClick={async()=>{ if(newPw!==confirmPw){toast.error("Passwords don't match");return;} if(newPw.length<8){toast.error("Min 8 characters");return;}
                try{ await api().post("/auth/change-password",{current_password:currentPw,new_password:newPw}); toast.success("Password updated"); setCurrentPw("");setNewPw("");setConfirmPw(""); }catch{toast.error("Failed");} }}
                className="px-4 py-2 bg-[#00d4aa] text-black text-sm font-bold rounded-lg hover:bg-[#00bfa5] transition-colors">Update password</button>
            </div>
          </div>
          <div className="bg-[#111318] border border-[#1f2530] rounded-xl p-5">
            <h2 className="text-sm font-bold text-[#e8ecf2] mb-3">Account</h2>
            <div className="text-xs text-[#8892a4] space-y-1.5">
              {[["Email",user?.email],["Role",user?.role],["Workspace",tenant?.name],["Daily AI query limit",String(tenant?.queryLimitPerDay)]].map(([k,v])=>(
                <div key={k} className="flex justify-between"><span className="text-[#4a5568]">{k}</span><span className="capitalize">{v}</span></div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab==="apikeys" && (
        <div className="space-y-4">
          {revealedKey && (
            <div className="bg-[rgba(0,212,170,0.08)] border border-[rgba(0,212,170,0.3)] rounded-xl p-4">
              <p className="text-xs font-bold text-[#00d4aa] mb-2">⚠ Copy this key now — it won't be shown again</p>
              <div className="flex items-center gap-2 bg-[#0a0c10] rounded-lg px-3 py-2">
                <code className="flex-1 text-xs text-[#e8ecf2] font-mono break-all">{showReveal?revealedKey:revealedKey.replace(/./g,"•")}</code>
                <button onClick={()=>setShowReveal(v=>!v)} className="text-[#4a5568] hover:text-[#e8ecf2]">{showReveal?<EyeOff size={13}/>:<Eye size={13}/>}</button>
                <button onClick={copyKey} className="text-[#4a5568] hover:text-[#00d4aa] transition-colors">{copied?<Check size={13} className="text-[#00d4aa]"/>:<Copy size={13}/>}</button>
              </div>
              <button onClick={()=>setRevealedKey(null)} className="text-[10px] text-[#4a5568] mt-2 hover:text-[#8892a4]">I've saved it — dismiss</button>
            </div>
          )}
          <div className="bg-[#111318] border border-[#1f2530] rounded-xl p-5">
            <h2 className="text-sm font-bold text-[#e8ecf2] mb-4">Create API key</h2>
            <div className="space-y-3 max-w-md">
              <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Key name</label>
                <input value={newKeyName} onChange={e=>setNewKeyName(e.target.value)} placeholder="e.g. CI pipeline, Zapier"
                  className="w-full px-3 py-2 bg-[#181c24] border border-[#2a3040] rounded-lg text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"/></div>
              <div><label className="block text-[10px] font-mono text-[#4a5568] mb-2 uppercase tracking-wider">Scopes</label>
                <div className="space-y-1">{SCOPES.map(s=>(
                  <label key={s.value} className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={newKeyScopes.includes(s.value)} onChange={e=>setNewKeyScopes(p=>e.target.checked?[...p.filter(x=>x!=="*"),s.value]:p.filter(x=>x!==s.value))} className="accent-[#00d4aa]"/>
                    <span className="text-xs text-[#8892a4]"><span className="font-mono text-[#00d4aa]">{s.value}</span> — {s.desc}</span>
                  </label>
                ))}</div>
              </div>
              <div><label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">Expiry</label>
                <select value={newKeyExpiry??""} onChange={e=>setNewKeyExpiry(e.target.value?Number(e.target.value):null)}
                  className="w-full px-3 py-2 bg-[#181c24] border border-[#2a3040] rounded-lg text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa]">
                  <option value="">Never</option><option value="30">30 days</option><option value="90">90 days</option><option value="365">1 year</option>
                </select>
              </div>
              <button onClick={()=>createKey.mutate({name:newKeyName,scopes:newKeyScopes,expires_days:newKeyExpiry??undefined})}
                disabled={!newKeyName.trim()||createKey.isPending}
                className={cn("flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-lg transition-colors",newKeyName.trim()?"bg-[#00d4aa] text-black hover:bg-[#00bfa5]":"bg-[#1f2530] text-[#4a5568] cursor-not-allowed")}>
                {createKey.isPending?<><Loader2 size={12} className="animate-spin"/>Creating…</>:<><Plus size={12}/>Create API key</>}
              </button>
            </div>
          </div>
          <div className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-[#1f2530]"><span className="text-xs font-bold text-[#e8ecf2]">Active keys ({keysQ.data?.length??0})</span></div>
            {!keysQ.data?.length?<p className="text-xs text-[#4a5568] text-center py-8">No API keys yet</p>:keysQ.data.map(k=>(
              <div key={k.id} className="flex items-center gap-3 px-5 py-3 border-b border-[#1f2530] last:border-0">
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-[#e8ecf2] truncate">{k.name}</div>
                  <div className="text-[10px] font-mono text-[#4a5568]">{k.prefix}••••••••</div>
                  <div className="flex gap-1 mt-1">{k.scopes.map(s=><span key={s} className="text-[9px] font-mono px-1.5 py-0.5 bg-[rgba(0,212,170,0.08)] text-[#00d4aa] rounded">{s}</span>)}</div>
                </div>
                <div className="text-[10px] text-[#4a5568] text-right mr-2">{k.last_used_at?`Used ${new Date(k.last_used_at).toLocaleDateString()}`:"Never used"}</div>
                <button onClick={()=>revokeKey.mutate(k.id)} className="text-[#4a5568] hover:text-[#ff4757] transition-colors"><Trash2 size={13}/></button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab==="sessions" && (
        <div className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-[#1f2530] flex items-center justify-between">
            <span className="text-xs font-bold text-[#e8ecf2]">Active sessions ({sessQ.data?.length??0})</span>
            <button onClick={()=>api().post("/auth/logout-all").then(()=>{toast.success("All sessions revoked");sessQ.refetch();})}
              className="text-[10px] text-[#ff4757] hover:underline flex items-center gap-1"><LogOut size={10}/>Revoke all</button>
          </div>
          {!sessQ.data?.length?<p className="text-xs text-[#4a5568] text-center py-8">No active sessions</p>:sessQ.data.map(s=>(
            <div key={s.id} className="flex items-center gap-3 px-5 py-3 border-b border-[#1f2530] last:border-0">
              <Monitor size={15} className="text-[#4a5568] flex-shrink-0"/>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[#e8ecf2] truncate">{s.device||"Unknown device"}</div>
                <div className="text-[10px] text-[#4a5568]">{s.ip} · {new Date(s.created_at).toLocaleDateString()}</div>
              </div>
              <button onClick={()=>revokeSession.mutate(s.id)} className="text-[#4a5568] hover:text-[#ff4757] transition-colors"><Trash2 size={13}/></button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
