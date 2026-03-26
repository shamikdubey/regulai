import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AppState {
  selectedJurisdiction: string | null;
  selectedDomain: string | null;
  sidebarOpen: boolean;
  // Actions
  setSelectedJurisdiction: (j: string | null) => void;
  setSelectedDomain: (d: string | null) => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      selectedJurisdiction: null,
      selectedDomain: null,
      sidebarOpen: true,
      setSelectedJurisdiction: (j) => set({ selectedJurisdiction: j }),
      setSelectedDomain: (d) => set({ selectedDomain: d }),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
    }),
    {
      name: "regulai-app-v4",
      partialize: (s) => ({
        sidebarOpen: s.sidebarOpen,
        selectedJurisdiction: s.selectedJurisdiction,
        selectedDomain: s.selectedDomain,
      }),
    }
  )
);
