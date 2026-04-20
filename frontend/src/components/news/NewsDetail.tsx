import { useQuery } from '@tanstack/react-query'
import { ExternalLink, X } from 'lucide-react'
import { fetchNewsItem } from '../../api/news'
import { useUIStore } from '../../store/uiStore'
import ImportanceBadge from '../shared/ImportanceBadge'
import LoadingSpinner from '../shared/LoadingSpinner'
import TagChip from '../shared/TagChip'
import BalancedTake from './BalancedTake'

export default function NewsDetail({ itemId }: { itemId: number }) {
  const { closeDetail, openDetail, setActiveTab } = useUIStore()
  const { data: item, isLoading } = useQuery({
    queryKey: ['news', itemId],
    queryFn: () => fetchNewsItem(itemId),
  })

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={closeDetail} />
      <aside className="relative w-full max-w-2xl bg-stone-950 border-l border-stone-800 flex flex-col overflow-hidden animate-[slideIn_0.2s_ease-out]">
        <div className="flex items-center justify-between p-4 border-b border-stone-800">
          <span className="text-sm font-semibold text-stone-300">Article Detail</span>
          <button onClick={closeDetail} className="p-1.5 rounded-lg text-stone-500 hover:text-stone-200 hover:bg-stone-800 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
          {item && (
            <>
              <div className="flex items-start gap-2">
                <ImportanceBadge rank={item.importance_rank} />
                <div className="flex-1">
                  <h2 className="text-base font-semibold text-stone-100 leading-snug">{item.headline}</h2>
                  <div className="flex items-center gap-2 mt-1 text-xs text-stone-500">
                    {item.source_name && <span>{item.source_name}</span>}
                    {item.published_at && <span>· {new Date(item.published_at).toLocaleDateString()}</span>}
                    <span className="uppercase">{item.language}</span>
                  </div>
                </div>
                <a href={item.external_url} target="_blank" rel="noopener noreferrer"
                  className="p-1.5 rounded-lg text-stone-500 hover:text-orange-400 hover:bg-stone-800 transition-colors">
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>

              {item.why_it_matters && (
                <div className="bg-orange-950/30 border border-orange-900/50 rounded-lg p-3">
                  <p className="text-xs font-semibold text-orange-400 uppercase tracking-wide mb-1">Why it matters</p>
                  <p className="text-sm text-orange-100 leading-relaxed">{item.why_it_matters}</p>
                </div>
              )}

              {item.summary && (
                <div>
                  <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-1.5">Summary</p>
                  <p className="text-sm text-stone-300 leading-relaxed">{item.summary}</p>
                </div>
              )}

              <BalancedTake pros={item.pros} cons={item.cons} balancedTake={item.balanced_take} />

              {(item.vendors.length > 0 || item.verticals.length > 0) && (
                <div>
                  <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-2">Tagged</p>
                  <div className="flex flex-wrap gap-1.5">
                    {item.vendors.map((v) => (
                      <TagChip key={v.id} label={v.name} color="orange"
                        onClick={() => { setActiveTab('vendors'); openDetail('vendor', v.id) }} />
                    ))}
                    {item.verticals.map((v) => (
                      <TagChip key={v.id} label={v.name} color="blue"
                        onClick={() => { setActiveTab('verticals'); openDetail('vertical', v.id) }} />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </aside>

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}
