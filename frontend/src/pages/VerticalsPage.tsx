import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchVerticals } from '../api/verticals'
import VerticalCard from '../components/verticals/VerticalCard'
import VerticalDetail from '../components/verticals/VerticalDetail'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SearchBar from '../components/shared/SearchBar'
import { useUIStore } from '../store/uiStore'

export default function VerticalsPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['verticals', { search }],
    queryFn: () => fetchVerticals(search),
  })
  const { detailItem, openDetail } = useUIStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-stone-200">Industry Verticals</h2>
        {data && <span className="text-xs text-stone-500">{data.total} sectors</span>}
      </div>
      <SearchBar placeholder="Search verticals…" value={search} onChange={setSearch} />
      {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
      {!isLoading && !data?.verticals.length && (
        <EmptyState title="No verticals" description="Industry sectors are seeded on startup" icon="🏭" />
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {data?.verticals.map((v: { id: number; name: string; slug: string; description: string | null; icon_name: string | null; news_count: number }) => (
          <VerticalCard key={v.id} vertical={v} onClick={() => openDetail('vertical', v.id)} />
        ))}
      </div>
      {detailItem?.type === 'vertical' && <VerticalDetail verticalId={detailItem.id} />}
    </div>
  )
}
