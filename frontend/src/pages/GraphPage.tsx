import { useQuery } from '@tanstack/react-query'
import { fetchEntityGraph } from '../api/graph'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import TopicSelect from '../components/shared/TopicSelect'
import EntityGraphView from '../components/graph/EntityGraphView'
import { useFilterStore } from '../store/filterStore'
import type { EntityGraphNetwork } from '../types'

function fmtScore(value: number): string {
  return value >= 100 ? value.toFixed(0) : value.toFixed(1)
}

export default function GraphPage() {
  const { selectedTopicId, setFilter } = useFilterStore()
  const { data, isLoading } = useQuery<EntityGraphNetwork>({
    queryKey: ['graph', selectedTopicId],
    queryFn: () => fetchEntityGraph(selectedTopicId || undefined),
  })

  const hasGraph = (data?.nodes.length ?? 0) > 1 && (data?.links.length ?? 0) > 0
  const strongestLink = data?.links.reduce((best, link) => (
    !best || link.strength_score > best.strength_score ? link : best
  ), null as EntityGraphNetwork['links'][number] | null)
  const topNode = data?.nodes[0] ?? null

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <div>
            <h2 className="text-lg font-semibold text-stone-200">Entity Graph</h2>
            <p className="text-sm text-stone-500">
              Node size shows entity importance. Link thickness shows relationship strength.
            </p>
          </div>
          {data && (
            <p className="text-xs text-stone-600">
              Scope: <span className="text-stone-400">{data.scope_label}</span>
            </p>
          )}
        </div>
        <div className="w-full lg:w-56">
          <TopicSelect value={selectedTopicId} onChange={(value) => setFilter('selectedTopicId', value)} />
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-stone-800 bg-stone-900 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-stone-500">Nodes</p>
            <p className="mt-2 text-2xl font-semibold text-stone-100">{data.node_count}</p>
            <p className="mt-1 text-xs text-stone-500">Visible entities and themes in this network.</p>
          </div>
          <div className="rounded-xl border border-stone-800 bg-stone-900 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-stone-500">Links</p>
            <p className="mt-2 text-2xl font-semibold text-stone-100">{data.link_count}</p>
            <p className="mt-1 text-xs text-stone-500">
              {strongestLink ? `${strongestLink.article_count} shared articles on the strongest edge.` : 'No strong relationships yet.'}
            </p>
          </div>
          <div className="rounded-xl border border-stone-800 bg-stone-900 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.16em] text-stone-500">Top Node</p>
            <p className="mt-2 text-lg font-semibold text-orange-300">{topNode?.name ?? 'None yet'}</p>
            <p className="mt-1 text-xs text-stone-500">
              {topNode ? `${fmtScore(topNode.importance_score)} weighted importance across ${topNode.article_count} articles.` : 'Run ingestion to create graph data.'}
            </p>
          </div>
        </div>
      )}

      {isLoading && <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>}

      {!isLoading && !hasGraph && (
        <div className="rounded-2xl border border-dashed border-stone-800 bg-stone-900/60">
          <EmptyState
            title="Not enough linked entities yet"
            description="The graph appears once articles have overlapping entity and theme tags in the selected scope."
            icon="~"
          />
        </div>
      )}

      {data && hasGraph && <EntityGraphView graph={data} />}
    </div>
  )
}
