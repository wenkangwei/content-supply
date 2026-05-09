import { create } from 'zustand'

interface AppStore {
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}

export const useAppStore = create<AppStore>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}))
