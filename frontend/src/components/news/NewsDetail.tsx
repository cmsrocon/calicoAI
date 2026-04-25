import { useQuery } from '@tanstack/react-query'
import { ExternalLink, Link2, Loader2, X } from 'lucide-react'
import { fetchNewsItem } from '../../api/news'
import { fetchIngestionStatus } from '../../api/ingestion'
import { useUIStore } from '../../store/uiStore'
import ImportanceBadge from '../shared/ImportanceBadge'
import LoadingSpinner from '../shared/LoadingSpinner'
import TagChip from '../shared/TagChip'
import BalancedTake from './BalancedTake'

function formatProcessingError(error: string) {
  const normalized = error.trim()
  if (
    normalized === 'Expecting value: line 1 column 1 (char 0)' ||
    normalized.includes('LLM returned an empty response') ||
    normalized.includes('LLM returned an empty fenced response') ||
    normalized.includes('LLM returned invalid JSON')
  ) {
    return 'The configured model returned an empty or non-JSON response. Check Settings > Test connection, then run Refresh again.'
  }
  return normalized
}

export default function NewsDetail({ itemId }: { itemId: number }) {
  const { closeDetail, openDetail, setActiveTab } = useUIStore()
  const { data: item, isLoading } = useQuery({
    queryKey: ['news', itemId],
    queryFn: () => fetchNewsItem(itemId),
    refetchInterval: (query) => {
      const data = query.state.data as { is_processed?: boolean } | undefined
      return data && !data.is_processed ? 5000 : false
    },
  })

  const { data: ingestionStatus } = useQuery({
    queryKey: ['ingestion-status-detail'],
    queryFn: fetchIngestionStatus,
    refetchInterval: item && !item.is_processed ? 3000 : false,
    enabled: !!(item && !item.is_processed),
  })

  const missingFields = item && !item.is_processed ? [
    !item.summary && 'Summary',
    !item.why_it_matters && 'Why it matters',
    item.vendors.length === 0 && 'Entity tags',
    item.verticals.length === 0 && 'Theme tags',
    !item.balanced_take && 'Balanced analysis',
  ].filter(Boolean) as string[] : []

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={closeDetail} />
      <aside className="relative flex w-full max-w-2xl flex-col overflow-hidden border-l border-stone-800 bg-stone-950 animate-[slideIn_0.2s_ease-out]">
        <div className="flex items-center justify-between border-b border-stone-800 p-4">
          <span className="text-sm font-semibold text-stone-300">Article Detail</span>
          <button
            onClick={closeDetail}
            className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-800 hover:text-stone-200"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto p-4">
          {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
          {item && (
            <>
              <div className="flex items-start gap-2">
                <ImportanceBadge rank={item.importance_rank} />
                <div className="flex-1">
                  <h2 className="text-base font-semibold leading-snug text-stone-100">{item.headline}</h2>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-stone-500">
                    <span className="text-amber-300">{item.topic_name}</span>
                    {item.source_name && <span>{item.source_name}</span>}
                    {item.source_documents.length > 1 && <span>{item.source_documents.length} sources</span>}
                    {item.published_at && <span>{new Date(item.published_at).toLocaleDateString()}</span>}
                    <span className="uppercase">{item.language}</span>
                  </div>
                </div>
                <a
                  href={item.external_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-800 hover:text-orange-400"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>

              {!item.is_processed && (
                <div className="space-y-2 rounded-lg border border-yellow-800/50 bg-yellow-950/30 p-3">
                  <div className="flex items-center gap-2">
                    {ingestionStatus?.is_running ? (
                      <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-yellow-400" />
                    ) : (
                      <span className="text-yellow-400">...</span>
                    )}
                    <p className="text-xs font-semibold text-yellow-400">
                      {ingestionStatus?.is_running ? 'Analysis in progress' : 'Analysis incomplete'}
                    </p>
                  </div>

                  {ingestionStatus?.is_running && ingestionStatus.current_stage && (
                    <div className="ml-5 space-y-0.5">
                      <p className="text-xs text-orange-300">{ingestionStatus.current_stage}</p>
                      {ingestionStatus.current_stage_detail && (
                        <p className="text-xs text-stone-500">{ingestionStatus.current_stage_detail}</p>
                      )}
                      {(ingestionStatus.live_calls ?? 0) > 0 && (
                        <p className="font-mono text-xs text-stone-600">
                          {ingestionStatus.live_calls} LLM calls
                          {ingestionStatus.live_cost_usd != null && ingestionStatus.live_cost_usd > 0
                            ? ` · $${ingestionStatus.live_cost_usd.toFixed(4)} est.`
                            : ''}
                        </p>
                      )}
                    </div>
                  )}

                  {missingFields.length > 0 && (
                    <ul className="ml-5 space-y-0.5">
                      {missingFields.map((field) => (
                        <li key={field} className="text-xs text-yellow-200/60">- {field} not yet generated</li>
                      ))}
                    </ul>
                  )}

                  {item.processing_error && (
                    <p className="ml-5 text-xs text-red-400/80" title={item.processing_error}>
                      Error: {formatProcessingError(item.processing_error)}
                    </p>
                  )}

                  {!ingestionStatus?.is_running && (
                    <p className="ml-5 text-xs text-stone-500">Will be completed on the next ingestion run.</p>
                  )}
                </div>
              )}

              {item.why_it_matters && (
                <div className="rounded-lg border border-orange-900/50 bg-orange-950/30 p-3">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-orange-400">Why it matters</p>
                  <p className="text-sm leading-relaxed text-orange-100">{item.why_it_matters}</p>
                </div>
              )}

              {item.summary && (
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-stone-400">Summary</p>
                  <p className="text-sm leading-relaxed text-stone-300">{item.summary}</p>
                </div>
              )}

              {item.source_documents.length > 0 && (
                <div>
                  <div className="mb-2 flex items-center gap-1.5">
                    <Link2 className="h-3.5 w-3.5 text-sky-400" />
                    <p className="text-xs font-semibold uppercase tracking-wide text-stone-400">Source documents</p>
                  </div>
                  <div className="space-y-2">
                    {item.source_documents.map((source) => (
                      <a
                        key={`${source.url}-${source.headline}`}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block rounded-lg border border-stone-800 bg-stone-900 px-3 py-2 transition-colors hover:border-stone-600 hover:bg-stone-800"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <p className="line-clamp-2 text-sm font-medium text-stone-100">{source.headline}</p>
                            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-stone-500">
                              {source.source_name && <span>{source.source_name}</span>}
                              {source.published_at && <span>{new Date(source.published_at).toLocaleDateString()}</span>}
                              {source.is_primary && <span className="text-orange-300">Primary link</span>}
                            </div>
                          </div>
                          <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              <BalancedTake pros={item.pros} cons={item.cons} balancedTake={item.balanced_take} />

              {(item.vendors.length > 0 || item.verticals.length > 0) && (
                <div>
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-stone-400">Tagged</p>
                  <div className="flex flex-wrap gap-1.5">
                    {item.vendors.map((vendor) => (
                      <TagChip
                        key={vendor.id}
                        label={vendor.name}
                        color="orange"
                        onClick={() => {
                          setActiveTab('vendors')
                          openDetail('vendor', vendor.id)
                        }}
                      />
                    ))}
                    {item.verticals.map((vertical) => (
                      <TagChip
                        key={vertical.id}
                        label={vertical.name}
                        color="blue"
                        onClick={() => {
                          setActiveTab('verticals')
                          openDetail('vertical', vertical.id)
                        }}
                      />
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
