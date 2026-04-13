import { useState } from "react";
import { Navigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Users, Building2, BarChart2, Loader2, RefreshCw,
  ShieldAlert, Trash2, UserCheck, UserX, ChevronDown, ChevronUp,
  Search, UserPlus, X,
} from "lucide-react";
import toast from "react-hot-toast";
import { getApiClient } from "@/lib/api";
import { useAuthStore } from "@/stores/authStore";
import { cn } from "@/lib/utils";

// ── Types ─────────────────────────────────────────────────────────────────────

type AdminUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
};

type Tenant = {
  id: string;
  name: string;
  slug: string;
  allowed_jurisdictions: string[];
  allowed_domains: string[];
  query_limit_per_day: number;
  created_at: string;
  user_count?: number;
};

type AdminStats = {
  total_users: number;
  active_users: number;
  total_tenants: number;
  total_queries_today: number;
  total_queries_this_month: number;
  total_documents: number;
  total_gap_assessments: number;
  avg_response_ms: number;
};

type Tab = "stats" | "users" | "tenants";

// ── Component ─────────────────────────────────────────────────────────────────

export default function AdminPanelPage() {
  const user = useAuthStore((s) => s.user);

  // ── All hooks must come before the conditional return ──────────────────────
  const [tab, setTab]                       = useState<Tab>("stats");
  const [expandedTenant, setExpandedTenant] = useState<string | null>(null);
  const [userSearch, setUserSearch]         = useState("");
  const [inviteOpen, setInviteOpen]         = useState(false);
  const [inviteEmail, setInviteEmail]       = useState("");
  const [inviteRole, setInviteRole]         = useState<"user" | "admin">("user");
  const qc = useQueryClient();

  // ── Queries ────────────────────────────────────────────────────────────────

  const statsQ = useQuery({
    queryKey: ["admin-stats"],
    queryFn: () =>
      getApiClient().get<AdminStats>("/admin/stats").then((r) => r.data),
    enabled: tab === "stats" && user?.role === "admin",
  });

  const usersQ = useQuery({
    queryKey: ["admin-users"],
    queryFn: () =>
      getApiClient().get<AdminUser[]>("/admin/users").then((r) => r.data),
    enabled: tab === "users" && user?.role === "admin",
  });

  const tenantsQ = useQuery({
    queryKey: ["admin-tenants"],
    queryFn: () =>
      getApiClient().get<Tenant[]>("/admin/tenants").then((r) => r.data),
    enabled: tab === "tenants" && user?.role === "admin",
  });

  // ── Mutations ──────────────────────────────────────────────────────────────

  const toggleUserMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      getApiClient()
        .patch<AdminUser>(`/admin/users/${id}`, { is_active })
        .then((r) => r.data),
    onSuccess: (data) => {
      toast.success(
        data.is_active ? `${data.full_name} activated` : `${data.full_name} deactivated`,
      );
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => toast.error("Failed to update user"),
  });

  const deleteUserMutation = useMutation({
    mutationFn: (id: string) => getApiClient().delete(`/admin/users/${id}`),
    onSuccess: () => {
      toast.success("User deleted");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => toast.error("Failed to delete user"),
  });

  const inviteMutation = useMutation({
    mutationFn: (payload: { email: string; role: string }) =>
      getApiClient().post("/auth/invite", payload).then((r) => r.data),
    onSuccess: () => {
      toast.success(`Invitation sent to ${inviteEmail}`);
      setInviteOpen(false);
      setInviteEmail("");
      setInviteRole("user");
      qc.invalidateQueries({ queryKey: ["admin-users"] });
    },
    onError: () => toast.error("Failed to send invitation"),
  });

  // ── Access guard (after all hooks) ─────────────────────────────────────────
  if (!user || user.role !== "admin") {
    return <Navigate to="/dashboard" replace />;
  }

  // ── Derived state ──────────────────────────────────────────────────────────

  const filteredUsers = (usersQ.data ?? []).filter(
    (u) =>
      userSearch === "" ||
      u.full_name?.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email?.toLowerCase().includes(userSearch.toLowerCase()),
  );

  const TABS: { key: Tab; label: string; icon: typeof BarChart2 }[] = [
    { key: "stats",   label: "Overview", icon: BarChart2  },
    { key: "users",   label: "Users",    icon: Users      },
    { key: "tenants", label: "Tenants",  icon: Building2  },
  ];

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 max-w-5xl mx-auto">

      {/* ── Invite modal ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {inviteOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 z-40"
              onClick={() => setInviteOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 8 }}
              transition={{ duration: 0.15 }}
              className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
            >
              <div
                className="w-full max-w-md bg-[#111318] border border-[#1f2530] rounded-2xl p-6 pointer-events-auto"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Modal header */}
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <h2 className="text-sm font-bold text-[#e8ecf2]">
                      Invite User
                    </h2>
                    <p className="text-[10px] text-[#4a5568] mt-0.5">
                      Send an invitation email to add a new team member
                    </p>
                  </div>
                  <button
                    onClick={() => setInviteOpen(false)}
                    className="text-[#4a5568] hover:text-[#e8ecf2] transition-colors"
                  >
                    <X size={15} />
                  </button>
                </div>

                {/* Email */}
                <div className="mb-4">
                  <label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">
                    Email address *
                  </label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    className="w-full px-3 py-2 bg-[#0a0c10] border border-[#2a3040] rounded-xl text-sm text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"
                    autoFocus
                  />
                </div>

                {/* Role */}
                <div className="mb-6">
                  <label className="block text-[10px] font-mono text-[#4a5568] mb-1 uppercase tracking-wider">
                    Role
                  </label>
                  <div className="flex gap-2">
                    {(["user", "admin"] as const).map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setInviteRole(r)}
                        className={cn(
                          "flex-1 py-2 rounded-xl text-xs font-bold border capitalize transition-all",
                          inviteRole === r
                            ? "bg-[rgba(0,212,170,0.12)] border-[rgba(0,212,170,0.4)] text-[#00d4aa]"
                            : "border-[#2a3040] text-[#4a5568] hover:text-[#8892a4] hover:border-[#4a5568]",
                        )}
                      >
                        {r}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  <button
                    onClick={() => setInviteOpen(false)}
                    className="flex-1 py-2 rounded-xl text-xs font-bold border border-[#2a3040] text-[#4a5568] hover:text-[#8892a4] transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => {
                      if (!inviteEmail.trim()) {
                        toast.error("Enter an email address");
                        return;
                      }
                      inviteMutation.mutate({
                        email: inviteEmail.trim(),
                        role: inviteRole,
                      });
                    }}
                    disabled={inviteMutation.isPending || !inviteEmail.trim()}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-xs font-bold transition-all",
                      inviteMutation.isPending || !inviteEmail.trim()
                        ? "bg-[#1f2530] text-[#4a5568] cursor-not-allowed"
                        : "bg-[#00d4aa] text-black hover:bg-[#00bfa5]",
                    )}
                  >
                    {inviteMutation.isPending ? (
                      <Loader2 size={12} className="animate-spin" />
                    ) : (
                      <UserPlus size={12} />
                    )}
                    Send Invitation
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── Page header ───────────────────────────────────────────────────── */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <ShieldAlert size={16} className="text-[#00d4aa]" />
            <h1 className="text-xl font-bold text-[#e8ecf2]">Admin Panel</h1>
          </div>
          <p className="text-xs text-[#4a5568]">
            Manage users, tenants, and monitor system health — admin access only
          </p>
        </div>
        <button
          onClick={() => {
            qc.invalidateQueries({ queryKey: ["admin-stats"] });
            qc.invalidateQueries({ queryKey: ["admin-users"] });
            qc.invalidateQueries({ queryKey: ["admin-tenants"] });
          }}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#111318] border border-[#1f2530] rounded-xl text-xs text-[#8892a4] hover:text-[#e8ecf2] hover:border-[#2a3040] transition-all flex-shrink-0"
        >
          <RefreshCw size={12} />
          Refresh
        </button>
      </div>

      {/* ── Tabs ──────────────────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-[#111318] border border-[#1f2530] rounded-xl p-1 mb-6 w-fit">
        {TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold transition-all",
              tab === key
                ? "bg-[#00d4aa] text-black"
                : "text-[#4a5568] hover:text-[#8892a4]",
            )}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">

        {/* ── STATS TAB ─────────────────────────────────────────────────── */}
        {tab === "stats" && (
          <motion.div
            key="stats"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            {statsQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-20 text-[#4a5568]">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading stats…</span>
              </div>
            ) : statsQ.isError ? (
              <div className="py-20 text-center text-sm text-[#ff4757]">
                Failed to load stats
              </div>
            ) : statsQ.data ? (
              /* ✅ Fixed: 6 cards in md:grid-cols-3 for even 2×3 layout */
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {[
                  {
                    label: "Total Users",
                    value: statsQ.data.total_users,
                    sub: `${statsQ.data.active_users} active`,
                    color: "#00d4aa",
                  },
                  {
                    label: "Tenants",
                    value: statsQ.data.total_tenants,
                    sub: "organisations",
                    color: "#8892a4",
                  },
                  {
                    label: "Queries Today",
                    value: statsQ.data.total_queries_today,
                    sub: `${statsQ.data.total_queries_this_month} this month`,
                    color: "#f5a623",
                  },
                  {
                    label: "Documents",
                    value: statsQ.data.total_documents,
                    sub: "uploaded",
                    color: "#8892a4",
                  },
                  {
                    label: "Gap Assessments",
                    value: statsQ.data.total_gap_assessments,
                    sub: "all time",
                    color: "#8892a4",
                  },
                  {
                    label: "Avg Response",
                    value: `${statsQ.data.avg_response_ms}ms`,
                    sub: "per query",
                    color:
                      statsQ.data.avg_response_ms < 2000 ? "#00d4aa" : "#f5a623",
                  },
                ].map((stat) => (
                  <div
                    key={stat.label}
                    className="bg-[#111318] border border-[#1f2530] rounded-2xl p-5"
                  >
                    <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-2">
                      {stat.label}
                    </p>
                    <p
                      className="text-2xl font-bold font-mono"
                      style={{ color: stat.color }}
                    >
                      {stat.value}
                    </p>
                    <p className="text-[10px] text-[#4a5568] mt-1">{stat.sub}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </motion.div>
        )}

        {/* ── USERS TAB ─────────────────────────────────────────────────── */}
        {tab === "users" && (
          <motion.div
            key="users"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            {/* ✅ Search + invite row */}
            <div className="flex items-center gap-2 mb-4">
              <div className="relative flex-1">
                <Search
                  size={13}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-[#4a5568] pointer-events-none"
                />
                <input
                  value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)}
                  placeholder="Search by name or email…"
                  className="w-full pl-8 pr-3 py-2 bg-[#111318] border border-[#2a3040] rounded-xl text-xs text-[#e8ecf2] outline-none focus:border-[#00d4aa] transition-colors"
                />
                {userSearch && (
                  <button
                    onClick={() => setUserSearch("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#4a5568] hover:text-[#e8ecf2] transition-colors"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
              <button
                onClick={() => setInviteOpen(true)}
                className="flex items-center gap-1.5 px-3 py-2 bg-[#00d4aa] text-black rounded-xl text-xs font-bold hover:bg-[#00bfa5] active:scale-[0.98] transition-all flex-shrink-0"
              >
                <UserPlus size={13} />
                Invite User
              </button>
            </div>

            {usersQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-20 text-[#4a5568]">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading users…</span>
              </div>
            ) : usersQ.isError ? (
              <div className="py-20 text-center text-sm text-[#ff4757]">
                Failed to load users
              </div>
            ) : filteredUsers.length === 0 ? (
              <div className="py-20 text-center">
                <Users size={32} className="text-[#2a3040] mx-auto mb-3" />
                <p className="text-sm text-[#4a5568]">
                  {userSearch ? `No users matching "${userSearch}"` : "No users found"}
                </p>
                {userSearch && (
                  <button
                    onClick={() => setUserSearch("")}
                    className="mt-2 text-xs text-[#00d4aa] hover:underline"
                  >
                    Clear search
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-3">
                  {filteredUsers.length} of {(usersQ.data ?? []).length} user
                  {(usersQ.data ?? []).length !== 1 ? "s" : ""}
                  {userSearch && ` matching "${userSearch}"`}
                </p>
                {filteredUsers.map((u) => (
                  <div
                    key={u.id}
                    className="flex items-center gap-4 p-4 bg-[#111318] border border-[#1f2530] rounded-xl"
                  >
                    {/* Avatar */}
                    <div
                      className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0",
                        u.is_active
                          ? "bg-[rgba(0,212,170,0.12)] text-[#00d4aa]"
                          : "bg-[#1f2530] text-[#4a5568]",
                      )}
                    >
                      {u.full_name?.[0]?.toUpperCase() ?? "?"}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-xs font-medium text-[#e8ecf2] truncate">
                          {u.full_name}
                        </p>
                        <span
                          className={cn(
                            "text-[9px] font-bold px-1.5 py-0.5 rounded font-mono uppercase",
                            u.role === "admin"
                              ? "bg-[rgba(0,212,170,0.12)] text-[#00d4aa]"
                              : "bg-[#1f2530] text-[#4a5568]",
                          )}
                        >
                          {u.role}
                        </span>
                      </div>
                      <p className="text-[10px] text-[#4a5568] font-mono mt-0.5 truncate">
                        {u.email}
                      </p>
                      {u.last_login && (
                        <p className="text-[9px] text-[#2a3040] font-mono mt-0.5">
                          Last login:{" "}
                          {new Date(u.last_login).toLocaleDateString()}
                        </p>
                      )}
                    </div>

                    {/* Status badge */}
                    <span
                      className={cn(
                        "text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0",
                        u.is_active
                          ? "bg-[rgba(0,212,170,0.12)] text-[#00d4aa]"
                          : "bg-[rgba(255,71,87,0.1)] text-[#ff4757]",
                      )}
                    >
                      {u.is_active ? "Active" : "Inactive"}
                    </span>

                    {/* Actions — guard: can't act on own account */}
                    {u.id !== user.id && (
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <button
                          onClick={() =>
                            toggleUserMutation.mutate({
                              id: u.id,
                              is_active: !u.is_active,
                            })
                          }
                          disabled={toggleUserMutation.isPending}
                          title={u.is_active ? "Deactivate" : "Activate"}
                          className="p-1.5 rounded-lg text-[#4a5568] hover:text-[#00d4aa] hover:bg-[rgba(0,212,170,0.08)] transition-all"
                        >
                          {u.is_active ? (
                            <UserX size={13} />
                          ) : (
                            <UserCheck size={13} />
                          )}
                        </button>
                        <button
                          onClick={() => {
                            if (
                              window.confirm(
                                `Delete ${u.full_name}? This cannot be undone.`,
                              )
                            ) {
                              deleteUserMutation.mutate(u.id);
                            }
                          }}
                          disabled={deleteUserMutation.isPending}
                          title="Delete user"
                          className="p-1.5 rounded-lg text-[#4a5568] hover:text-[#ff4757] hover:bg-[rgba(255,71,87,0.08)] transition-all"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {/* ── TENANTS TAB ───────────────────────────────────────────────── */}
        {tab === "tenants" && (
          <motion.div
            key="tenants"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            {tenantsQ.isLoading ? (
              <div className="flex items-center justify-center gap-2 py-20 text-[#4a5568]">
                <Loader2 size={16} className="animate-spin" />
                <span className="text-sm">Loading tenants…</span>
              </div>
            ) : tenantsQ.isError ? (
              <div className="py-20 text-center text-sm text-[#ff4757]">
                Failed to load tenants
              </div>
            ) : (tenantsQ.data ?? []).length === 0 ? (
              <div className="py-20 text-center">
                <Building2 size={32} className="text-[#2a3040] mx-auto mb-3" />
                <p className="text-sm text-[#4a5568]">No tenants found</p>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-[10px] font-mono text-[#4a5568] uppercase tracking-wider mb-3">
                  {(tenantsQ.data ?? []).length} tenant
                  {(tenantsQ.data ?? []).length !== 1 ? "s" : ""}
                </p>
                {(tenantsQ.data ?? []).map((t) => (
                  <div
                    key={t.id}
                    className="bg-[#111318] border border-[#1f2530] rounded-xl overflow-hidden"
                  >
                    <button
                      className="w-full flex items-center justify-between p-4 text-left"
                      onClick={() =>
                        setExpandedTenant((p) => (p === t.id ? null : t.id))
                      }
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-[rgba(0,212,170,0.08)] flex items-center justify-center flex-shrink-0">
                          <Building2 size={14} className="text-[#00d4aa]" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-[#e8ecf2]">
                            {t.name}
                          </p>
                          <p className="text-[10px] text-[#4a5568] font-mono">
                            {t.slug}
                            {t.user_count !== undefined &&
                              ` · ${t.user_count} user${t.user_count !== 1 ? "s" : ""}`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0 ml-3">
                        <span className="text-[10px] font-mono text-[#4a5568]">
                          {t.query_limit_per_day}/day
                        </span>
                        {expandedTenant === t.id ? (
                          <ChevronUp size={13} className="text-[#4a5568]" />
                        ) : (
                          <ChevronDown size={13} className="text-[#4a5568]" />
                        )}
                      </div>
                    </button>

                    <AnimatePresence>
                      {expandedTenant === t.id && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <div className="px-4 pb-4 space-y-3 border-t border-[#1f2530] pt-3">
                            <div>
                              <p className="text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1.5">
                                Allowed jurisdictions
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {t.allowed_jurisdictions.length > 0 ? (
                                  t.allowed_jurisdictions.map((j) => (
                                    <span
                                      key={j}
                                      className="text-[10px] px-2 py-0.5 bg-[#0a0c10] border border-[#1f2530] rounded font-mono text-[#8892a4]"
                                    >
                                      {j}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-[10px] text-[#4a5568]">
                                    All
                                  </span>
                                )}
                              </div>
                            </div>
                            <div>
                              <p className="text-[9px] font-mono text-[#4a5568] uppercase tracking-wider mb-1.5">
                                Allowed domains
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {t.allowed_domains.length > 0 ? (
                                  t.allowed_domains.map((d) => (
                                    <span
                                      key={d}
                                      className="text-[10px] px-2 py-0.5 bg-[#0a0c10] border border-[#1f2530] rounded font-mono text-[#8892a4]"
                                    >
                                      {d}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-[10px] text-[#4a5568]">
                                    All
                                  </span>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center justify-between text-[10px] font-mono text-[#4a5568]">
                              <span>
                                Query limit: {t.query_limit_per_day}/day
                              </span>
                              <span>
                                Created:{" "}
                                {new Date(t.created_at).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
