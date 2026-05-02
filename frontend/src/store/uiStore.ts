import { create } from 'zustand'

type Tab = 'news' | 'vendors' | 'verticals' | 'trends' | 'graph' | 'settings' | 'admin'

interface UIState {
  activeTab: Tab
  detailItem: { type: 'news' | 'vendor' | 'vertical'; id: number } | null
  setActiveTab: (tab: Tab) => void
  openDetail: (type: 'news' | 'vendor' | 'vertical', id: number) => void
  closeDetail: () => void
}

export const useUIStore = create<UIState>((set) => ({
  activeTab: 'news',
  detailItem: null,
  setActiveTab: (tab) => set({ activeTab: tab, detailItem: null }),
  openDetail: (type, id) => set({ detailItem: { type, id } }),
  closeDetail: () => set({ detailItem: null }),
}))
