import { useQuery } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { fetchVertical, fetchVerticalNews } from '../../api/verticals'
import { useFilterStore } from '../../store/filterStore'
import { useUIStore } from '../../store/uiStore'
import LoadingSpinner from '../shared/LoadingSpinner'
import TrendSummary from '../trends/TrendSummary'

export default function VerticalDetail({ verticalId }: { verticalId: number }) {
  const { closeDetail } = useUIStore()
  const { selectedTopicId } = useFilterStore()
  const { data: vertical, isLoading } = useQuery({
    queryKey: ['verticals', verticalId, selectedTopicId],
    queryFn: () => fetchVertical(verticalId, selectedTopicId || undefined),
  })
  const { data: newsData } = useQuery({
    queryKey: ['verticals', verticalId, 'news', selectedTopicId],
    queryFn: () => fetchVerticalNews(verticalId, 1, selectedTopicId || undefined),
    enabled: !!vertical,
  })

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={closeDetail} />
      <aside className="relative w-full max-w-2xl bg-stone-950 border-l border-stone-800 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-stone-800">
          <span className="text-sm font-semibold text-stone-300">Theme</span>
          <button onClick={closeDetail} className="p-1.5 rounded-lg text-stone-500 hover:text-stone-200 hover:bg-stone-800 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
          {vertical && (
            <>
              <div>
                <h2 className="text-xl font-bold text-sky-400">{vertical.name}</h2>
                {vertical.description && <p className="text-sm text-stone-400 mt-1">{vertical.description}</p>}
                <p className="text-xs text-stone-600 mt-1">{vertical.news_count} articles tracked</p>
              </div>
              {vertical.trend && (
                <div>
                  <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">Trends</p>
                  <TrendSummary trend={vertical.trend} />
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
