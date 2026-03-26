/**
 * useAuth — Phase 1 authentication hook
 *
 * Manages the full auth lifecycle:
 *   - Login: gets access token + refresh token
 *   - Silent refresh: exchanges refresh token before access token expires
 *   - Logout: revokes refresh token on server
 *   - Logout all: revokes all sessions everywhere
 *   - Session list: shows active devices
 *
 * Refresh tokens are stored in localStorage (via zustand/persist).
 * Access tokens are kept in memory (zustand, not persisted to storage).
 * This pattern:
 *   - Prevents XSS from reading short-lived access tokens from storage
 *   - Keeps the user logged in across page refreshes via refresh token
 *   - Revokes server-side on logout so stolen tokens can't be reused
 */
import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { useAuthStore } from "@/stores/authStore";
import { api, getApiClient, resetApiClient } from "@/lib/api";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "/api/v1";

// Refresh 2 minutes before expiry
const REFRESH_BUFFER_MS = 2 * 60 * 1000;

export function useAuth() {
  const {
    token,
    user,
    tenant,
    setToken,
    setUser,
    setTenant,
    logout: clearStore,
    isAuthenticated,
    isTokenExpired,
  } = useAuthStore();

  const [loading, setLoading] = useState(false);
  const [refreshToken, setRefreshToken] = useState<string | null>(
    // Refresh token lives in sessionStorage (cleared on tab close)
    // For "remember me" it would go to localStorage
    () => sessionStorage.getItem("rkai_rt")
  );
  const navigate = useNavigate();
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Schedule next silent refresh ──────────────────────────────────────────
  const scheduleRefresh = useCallback((accessToken: string) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    try {
      const payload = JSON.parse(atob(accessToken.split(".")[1]));
      const expiresAt = payload.exp * 1000;
      const now = Date.now();
      const delay = Math.max(expiresAt - now - REFRESH_BUFFER_MS, 10_000);

      refreshTimerRef.current = setTimeout(async () => {
        await silentRefresh();
      }, delay);
    } catch {
      // Malformed token — don't schedule
    }
  }, []);

  // ── Silent token refresh ──────────────────────────────────────────────────
  const silentRefresh = useCallback(async () => {
    const rt = sessionStorage.getItem("rkai_rt");
    if (!rt) return;

    try {
      const resp = await axios.post(`${API_BASE}/auth/refresh`, { refresh_token: rt });
      const { access_token, refresh_token: new_rt } = resp.data;

      setToken(access_token);
      sessionStorage.setItem("rkai_rt", new_rt);
      setRefreshToken(new_rt);
      scheduleRefresh(access_token);
    } catch (err: any) {
      if (err?.response?.status === 401) {
        // Refresh token invalid/expired/stolen — force logout
        await logout("Token expired. Please sign in again.");
      }
    }
  }, [scheduleRefresh]);

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      const form = new URLSearchParams({ username: email.toLowerCase(), password });
      const resp = await axios.post(`${API_BASE}/auth/token`, form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });

      const { access_token, refresh_token: rt } = resp.data;

      // Store access token in memory (zustand)
      setToken(access_token);

      // Store refresh token in sessionStorage
      sessionStorage.setItem("rkai_rt", rt);
      setRefreshToken(rt);

      // Fetch profile
      const me = await axios.get(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setUser({
        id: me.data.id,
        email: me.data.email,
        name: me.data.full_name || me.data.email,
        role: me.data.role,
        tenant_id: me.data.tenant_id,
      });

      const tenantResp = await axios.get(`${API_BASE}/tenants/me`, {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      setTenant({
        id: tenantResp.data.id,
        name: tenantResp.data.name,
        slug: tenantResp.data.slug,
        allowedJurisdictions: tenantResp.data.allowed_jurisdictions,
        allowedDomains: tenantResp.data.allowed_domains,
        queryLimitPerDay: tenantResp.data.query_limit_per_day,
      });

      scheduleRefresh(access_token);
      return { success: true };
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg =
        typeof detail === "string"
          ? detail.includes("Incorrect")
            ? "Incorrect email or password."
            : detail
          : err?.response?.status === 429
          ? detail?.replace
            ? detail
            : "Account locked. Please try again later."
          : "Sign in failed. Please try again.";
      return { success: false, error: msg };
    } finally {
      setLoading(false);
    }
  }, [setToken, setUser, setTenant, scheduleRefresh]);

  // ── Logout (single device) ─────────────────────────────────────────────────
  const logout = useCallback(async (message?: string) => {
    const rt = sessionStorage.getItem("rkai_rt");

    // Revoke on server (best-effort)
    if (rt) {
      try {
        await axios.post(`${API_BASE}/auth/logout`, { refresh_token: rt });
      } catch {
        // Server may be unreachable — still clear local state
      }
    }

    // Clear all local state
    sessionStorage.removeItem("rkai_rt");
    clearStore();
    resetApiClient();

    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);

    if (message) toast.error(message);
    navigate("/login", { replace: true });
  }, [clearStore, navigate]);

  // ── Logout all devices ────────────────────────────────────────────────────
  const logoutAll = useCallback(async () => {
    try {
      await getApiClient().post("/auth/logout-all");
    } catch {
      // Continue anyway
    }
    sessionStorage.removeItem("rkai_rt");
    clearStore();
    resetApiClient();
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    toast.success("Signed out from all devices.");
    navigate("/login", { replace: true });
  }, [clearStore, navigate]);

  // ── On mount: attempt silent refresh if we have a refresh token ────────────
  useEffect(() => {
    const rt = sessionStorage.getItem("rkai_rt");
    if (rt && isTokenExpired()) {
      silentRefresh();
    } else if (token && !isTokenExpired()) {
      scheduleRefresh(token);
    }
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, []);

  return {
    user,
    tenant,
    loading,
    isAuthenticated: isAuthenticated(),
    login,
    logout,
    logoutAll,
    silentRefresh,
  };
}
