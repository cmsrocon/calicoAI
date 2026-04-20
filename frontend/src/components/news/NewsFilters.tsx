import { useFilterStore } from '../../store/filterStore'

export default function NewsFilters() {
  const { dateFrom, dateTo, minImportance, sortBy, search, setFilter, resetFilters } = useFilterStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide">Filters</p>
        <button onClick={resetFilters} className="text-xs text-stone-500 hover:text-orange-400 transition-colors">Reset</button>
      </div>

      <div>
        <label className="text-xs text-stone-500 mb-1 block">Sort by</label>
        <select
          value={sortBy}
          onChange={(e) => setFilter('sortBy', e.target.value as 'importance' | 'date')}
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        >
          <option value="importance">Importance</option>
          <option value="date">Date</option>
        </select>
      </div>

      <div>
        <label className="text-xs text-stone-500 mb-1 block">Min importance: {minImportance || 'any'}</label>
        <input
          type="range" min={0} max={10} value={minImportance}
          onChange={(e) => setFilter('minImportance', Number(e.target.value))}
          className="w-full accent-orange-500"
        />
      </div>

      <div>
        <label className="text-xs text-stone-500 mb-1 block">From date</label>
        <input
          type="date" value={dateFrom}
          onChange={(e) => setFilter('dateFrom', e.target.value)}
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        />
      </div>

      <div>
        <label className="text-xs text-stone-500 mb-1 block">To date</label>
        <input
          type="date" value={dateTo}
          onChange={(e) => setFilter('dateTo', e.target.value)}
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        />
      </div>
    </div>
  )
}
