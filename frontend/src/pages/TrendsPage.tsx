import { useQuery } from '@tanstack/react-query'
import { fetchOverallTrend, fetchVendorTrends, fetchVerticalTrends } from '../api/trends'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import TopicSelect from '../components/shared/TopicSelect'
import TrendSummary from '../components/trends/TrendSummary'
import { useFilterStore } from '../store/filterStore'
import type { Trend } from '../types'

interface VendorTrendEntry {
  trend: Trend
  vendor: { id: number; name: string; slug: string } | null
}

interface VerticalTrendEntry {
  trend: Trend
  vertical: { id: number; name: string; slug: string } | null
}

export default function TrendsPage() {
  const { selectedTopicId, setFilter } = useFilterStore()
  const { data: overall, isLoading } = useQuery<Trend | null>({
    queryKey: ['trends', 'overall', selectedTopicId],
    queryFn: () => fetchOverallTrend(selectedTopicId || undefined),
  })

  const { data: vendorData } = useQuery<{ trends: VendorTrendEntry[] }>({
    queryKey: ['trends', 'vendors', selectedTopicId],
    queryFn: () => fetchVendorTrends(10, selectedTopicId || undefined),
  })

  const { data: verticalData } = useQuery<{ trends: VerticalTrendEntry[] }>({
    queryKey: ['trends', 'verticals', selectedTopicId],
    queryFn: () => fetchVerticalTrends(10, selectedTopicId || undefined),
  })

  const hasVendorTrends = (vendorData?.trends.length ?? 0) > 0
  const hasVerticalTrends = (verticalData?.trends.length ?? 0) > 0

  return (
    <div className="space-y-10 max-w-3xl">
      <div className="w-full sm:w-56">
        <TopicSelect value={selectedTopicId} onChange={(value) => setFilter('selectedTopicId', value)} />
      </div>

      <section>
        <h2 className="text-lg font-semibold text-stone-200 mb-4">
          {selectedTopicId ? 'Topic Overview' : 'All-Topic Overview'}
        </h2>
        {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
        {!isLoading && !overall && (
          <EmptyState
            title="No trend data yet"
            description="Trends are generated after ingestion processes at least a few articles. Run a refresh to start."
          />
        )}
        {overall && (
          <div className="bg-stone-900 border border-stone-800 rounded-xl p-5">
            <TrendSummary trend={overall} />
          </div>
        )}
      </section>

      {hasVendorTrends && (
        <section>
          <h2 className="text-lg font-semibold text-stone-200 mb-4">By Entity</h2>
          <div className="space-y-4">
            {vendorData!.trends.map(({ trend, vendor }) => (
              <div key={trend.id} className="bg-stone-900 border border-stone-800 rounded-xl p-4">
                <p className="text-sm font-semibold text-orange-400 mb-3">{vendor?.name ?? 'Unknown entity'}</p>
                <TrendSummary trend={trend} />
              </div>
            ))}
          </div>
        </section>
      )}

      {hasVerticalTrends && (
        <section>
          <h2 className="text-lg font-semibold text-stone-200 mb-4">By Theme</h2>
          <div className="space-y-4">
            {verticalData!.trends.map(({ trend, vertical }) => (
              <div key={trend.id} className="bg-stone-900 border border-stone-800 rounded-xl p-4">
                <p className="text-sm font-semibold text-sky-400 mb-3">{vertical?.name ?? 'Unknown theme'}</p>
                <TrendSummary trend={trend} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
