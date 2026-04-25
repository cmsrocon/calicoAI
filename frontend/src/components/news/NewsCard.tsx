import { ExternalLink } from 'lucide-react'
import type { NewsItemSummary } from '../../types'
import { useUIStore } from '../../store/uiStore'
import ImportanceBadge from '../shared/ImportanceBadge'
import TagChip from '../shared/TagChip'

interface Props {
  item: NewsItemSummary
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const h = Math.floor(diff / 3600000)
  if (h < 1) return `${Math.floor(diff / 60000)}m ago`
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function NewsCard({ item }: Props) {
  const { openDetail, setActiveTab } = useUIStore()
  const sourceCount = item.source_documents.length || (item.source_name ? 1 : 0)

  return (
    <article
      className="border border-stone-800 rounded-xl p-4 hover:border-stone-600 transition-colors cursor-pointer group bg-stone-950 hover:bg-stone-900"
      onClick={() => openDetail('news', item.id)}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <ImportanceBadge rank={item.importance_rank} />
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-800/60">
              {item.topic_name}
            </span>
            {item.source_name && (
              <span className="text-xs text-stone-500">{item.source_name}</span>
            )}
            {sourceCount > 1 && (
              <span className="text-xs text-sky-300">{sourceCount} sources</span>
            )}
            <span className="text-xs text-stone-600">
              {timeAgo(item.published_at || item.ingested_at)}
            </span>
            {item.language !== 'en' && (
              <span className="text-xs text-stone-600 uppercase">{item.language}</span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-stone-100 line-clamp-2 group-hover:text-orange-300 transition-colors mb-1.5">
            {item.headline}
          </h3>
          {item.why_it_matters && (
            <p className="text-xs text-stone-400 line-clamp-2 mb-2">{item.why_it_matters}</p>
          )}
          <div className="flex flex-wrap gap-1.5">
            {item.vendors.slice(0, 3).map((v) => (
              <TagChip
                key={v.id}
                label={v.name}
                color="orange"
                onClick={(e) => {
                  e.stopPropagation()
                  setActiveTab('vendors')
                  openDetail('vendor', v.id)
                }}
              />
            ))}
            {item.verticals.slice(0, 3).map((v) => (
              <TagChip
                key={v.id}
                label={v.name}
                color="blue"
                onClick={(e) => {
                  e.stopPropagation()
                  setActiveTab('verticals')
                  openDetail('vertical', v.id)
                }}
              />
            ))}
          </div>
        </div>
        <a
          href={item.external_url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="shrink-0 p-1.5 rounded-lg text-stone-600 hover:text-orange-400 hover:bg-stone-800 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </article>
  )
}
