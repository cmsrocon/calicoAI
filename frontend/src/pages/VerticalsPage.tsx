import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchVerticals } from '../api/verticals'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SearchBar from '../components/shared/SearchBar'
import TopicSelect from '../components/shared/TopicSelect'
import VerticalDetail from '../components/verticals/VerticalDetail'
import VerticalCard from '../components/verticals/VerticalCard'
import { useFilterStore } from '../store/filterStore'
import { useUIStore } from '../store/uiStore'

export default function VerticalsPage() {
  const [search, setSearch] = useState('')
  const { selectedTopicId, setFilter } = useFilterStore()
  const { data, isLoading } = useQuery({
    queryKey: ['verticals', { search, topicId: selectedTopicId }],
    queryFn: () => fetchVerticals(search, selectedTopicId || undefined),
  })
  const { detailItem, openDetail } = useUIStore()

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-200">Themes</h2>
          {data && <span className="text-xs text-stone-500">{data.total} tracked</span>}
        </div>
        <div className="w-full sm:w-56">
          <TopicSelect value={selectedTopicId} onChange={(value) => setFilter('selectedTopicId', value)} />
        </div>
      </div>
      <SearchBar placeholder="Search themes..." value={search} onChange={setSearch} />
      {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
      {!isLoading && !data?.verticals.length && (
        <EmptyState title="No themes yet" description="Themes are discovered automatically from analysed articles" />
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {data?.verticals.map((theme: { id: number; name: string; slug: string; description: string | null; icon_name: string | null; news_count: number }) => (
          <VerticalCard key={theme.id} vertical={theme} onClick={() => openDetail('vertical', theme.id)} />
        ))}
      </div>
      {detailItem?.type === 'vertical' && <VerticalDetail verticalId={detailItem.id} />}
    </div>
  )
}
