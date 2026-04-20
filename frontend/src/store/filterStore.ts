import { create } from 'zustand'

interface FilterState {
  dateFrom: string
  dateTo: string
  vendorIds: number[]
  verticalIds: number[]
  sourceIds: number[]
  minImportance: number
  language: string
  search: string
  sortBy: 'importance' | 'date'
  setFilter: <K extends keyof Omit<FilterState, 'setFilter' | 'resetFilters'>>(
    key: K,
    value: FilterState[K]
  ) => void
  resetFilters: () => void
}

const defaults = {
  dateFrom: '',
  dateTo: '',
  vendorIds: [] as number[],
  verticalIds: [] as number[],
  sourceIds: [] as number[],
  minImportance: 0,
  language: '',
  search: '',
  sortBy: 'importance' as const,
}

export const useFilterStore = create<FilterState>((set) => ({
  ...defaults,
  setFilter: (key, value) => set({ [key]: value }),
  resetFilters: () => set(defaults),
}))
