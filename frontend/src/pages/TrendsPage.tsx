import { useQuery } from '@tanstack/react-query'
import { fetchOverallTrend, fetchVendorTrends, fetchVerticalTrends } from '../api/trends'
import TrendSummary from '../components/trends/TrendSummary'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
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
  const { data: overall, isLoading } = useQuery<Trend | null>({
    queryKey: ['trends', 'overall'],
    queryFn: fetchOverallTrend,
  })

  const { data: vendorData } = useQuery<{ trends: VendorTrendEntry[] }>({
    queryKey: ['trends', 'vendors'],
    queryFn: () => fetchVendorTrends(10),
  })

  const { data: verticalData } = useQuery<{ trends: VerticalTrendEntry[] }>({
    queryKey: ['trends', 'verticals'],
    queryFn: () => fetchVerticalTrends(10),
  })

  const hasVendorTrends = (vendorData?.trends.length ?? 0) > 0
  const hasVerticalTrends = (verticalData?.trends.length ?? 0) > 0

  return (
    <div className="space-y-10 max-w-3xl">
      {/* Overall */}
      <section>
        <h2 className="text-lg font-semibold text-stone-200 mb-4">AI Industry Overview</h2>
        {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
        {!isLoading && !overall && (
          <EmptyState
            title="No trend data yet"
            description="Trends are generated after ingestion processes at least a few articles. Run a refresh to start."
            icon="📈"
          />
        )}
        {overall && (
          <div className="bg-stone-900 border border-stone-800 rounded-xl p-5">
            <TrendSummary trend={overall} />
          </div>
        )}
      </section>

      {/* By vendor */}
      {hasVendorTrends && (
        <section>
          <h2 className="text-lg font-semibold text-stone-200 mb-4">By Vendor</h2>
          <div className="space-y-4">
            {vendorData!.trends.map(({ trend, vendor }) => (
              <div key={trend.id} className="bg-stone-900 border border-stone-800 rounded-xl p-4">
                <p className="text-sm font-semibold text-orange-400 mb-3">{vendor?.name ?? 'Unknown vendor'}</p>
                <TrendSummary trend={trend} />
              </div>
            ))}
          </div>
        </section>
      )}

      {/* By vertical */}
      {hasVerticalTrends && (
        <section>
          <h2 className="text-lg font-semibold text-stone-200 mb-4">By Sector</h2>
          <div className="space-y-4">
            {verticalData!.trends.map(({ trend, vertical }) => (
              <div key={trend.id} className="bg-stone-900 border border-stone-800 rounded-xl p-4">
                <p className="text-sm font-semibold text-blue-400 mb-3">{vertical?.name ?? 'Unknown sector'}</p>
                <TrendSummary trend={trend} />
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
