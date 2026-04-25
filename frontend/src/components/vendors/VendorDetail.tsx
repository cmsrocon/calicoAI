import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { fetchVendor, fetchVendorNews } from '../../api/vendors'
import { useFilterStore } from '../../store/filterStore'
import { useUIStore } from '../../store/uiStore'
import LoadingSpinner from '../shared/LoadingSpinner'
import TrendSummary from '../trends/TrendSummary'

export default function VendorDetail({ vendorId }: { vendorId: number }) {
  const { closeDetail } = useUIStore()
  const { selectedTopicId } = useFilterStore()
  const { data: vendor, isLoading } = useQuery({
    queryKey: ['vendors', vendorId, selectedTopicId],
    queryFn: () => fetchVendor(vendorId, selectedTopicId || undefined),
  })
  const { data: newsData } = useQuery({
    queryKey: ['vendors', vendorId, 'news', selectedTopicId],
    queryFn: () => fetchVendorNews(vendorId, 1, selectedTopicId || undefined),
    enabled: !!vendor,
  })

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={closeDetail} />
      <aside className="relative w-full max-w-2xl bg-stone-950 border-l border-stone-800 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-stone-800">
          <span className="text-sm font-semibold text-stone-300">Entity</span>
          <button onClick={closeDetail} className="p-1.5 rounded-lg text-stone-500 hover:text-stone-200 hover:bg-stone-800 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
          {vendor && (
            <>
              <div>
                <h2 className="text-xl font-bold text-orange-400">{vendor.name}</h2>
                {vendor.description && <p className="text-sm text-stone-400 mt-1">{vendor.description}</p>}
                <p className="text-xs text-stone-600 mt-1">{vendor.news_count} articles tracked</p>
              </div>
              {vendor.trend && (
                <div>
                  <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">Trends</p>
                  <TrendSummary trend={vendor.trend} />
                </div>
              )}
              {newsData?.items.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">Recent news</p>
                  <div className="space-y-2">
                    {newsData.items.map((item: { id: number; headline: string; importance_rank: number | null }) => (
                      <div key={item.id} className="text-xs text-stone-300 flex gap-2">
                        <span className="text-stone-600 shrink-0">{item.importance_rank ?? '-'}</span>
                        <span className="line-clamp-2">{item.headline}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
