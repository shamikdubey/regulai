/**
 * Auth Store — Web Edition
 *
 * Differences from Electron version:
 *  - No keytar (OS keychain) — uses localStorage via zustand/persist
 *  - Token expiry checked on focus and interval
 *  - Refresh token support ready (Phase 1 will add refresh endpoint)
 *  - Clears API client on logout
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { resetApiClient } from "@/lib/api";

interface UserProfile {
  id: string;
  email: string;
  name: string;
  role: string;
  tenant_id: string;
}

interface TenantProfile {
  id: string;
  name: string;
  slug: string;
  allowedJurisdictions: string[];
  allowedDomains: string[];
  queryLimitPerDay: number;
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  tenant: TenantProfile | null;
  // Actions
  setToken: (token: string) => void;
  setUser: (user: UserProfile) => void;
  setTenant: (tenant: TenantProfile) => void;
  logout: () => void;
  isAuthenticated: () => boolean;
  isTokenExpired: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      tenant: null,

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),
      setTenant: (tenant) => set({ tenant }),

      logout: () => {
        set({ token: null, user: null, tenant: null });
        // Reset axios instance so no stale auth headers remain
        resetApiClient();
        // Clear any sensitive data from localStorage immediately
        // (persist middleware will also clear on next write)
      },

      isAuthenticated: () => {
        const { token, user } = get();
        if (!token || !user) return false;
        // Also check token hasn't expired
        return !get().isTokenExpired();
      },

      isTokenExpired: () => {
        const { token } = get();
        if (!token) return true;
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          if (!payload.exp) return false;
          // Add 30s buffer to prevent edge-case expiry during requests
          return Date.now() / 1000 > payload.exp - 30;
        } catch {
          return true;
        }
      },
    }),
    {
      name: "regulai-auth-v4",
      storage: createJSONStorage(() => localStorage),
      // Only persist the minimum needed
      partialize: (s) => ({
        token: s.token,
        user: s.user,
        tenant: s.tenant,
      }),
    }
  )
);
