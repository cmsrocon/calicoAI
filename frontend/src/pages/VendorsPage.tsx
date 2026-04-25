import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchVendors } from '../api/vendors'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SearchBar from '../components/shared/SearchBar'
import TopicSelect from '../components/shared/TopicSelect'
import VendorDetail from '../components/vendors/VendorDetail'
import VendorCard from '../components/vendors/VendorCard'
import { useFilterStore } from '../store/filterStore'
import { useUIStore } from '../store/uiStore'

export default function VendorsPage() {
  const [search, setSearch] = useState('')
  const { selectedTopicId, setFilter } = useFilterStore()
  const { data, isLoading } = useQuery({
    queryKey: ['vendors', { search, topicId: selectedTopicId }],
    queryFn: () => fetchVendors(search, 1, 50, selectedTopicId || undefined),
  })
  const { detailItem, openDetail } = useUIStore()

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-200">Tracked Entities</h2>
          {data && <span className="text-xs text-stone-500">{data.total} tracked</span>}
        </div>
        <div className="w-full sm:w-56">
          <TopicSelect value={selectedTopicId} onChange={(value) => setFilter('selectedTopicId', value)} />
        </div>
      </div>
      <SearchBar placeholder="Search entities..." value={search} onChange={setSearch} />
      {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
      {!isLoading && !data?.vendors.length && (
        <EmptyState title="No entities yet" description="Entities are discovered automatically during ingestion" />
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data?.vendors.map((vendor: { id: number; name: string; slug: string; description: string | null; news_count: number }) => (
          <VendorCard key={vendor.id} vendor={vendor} onClick={() => openDetail('vendor', vendor.id)} />
        ))}
      </div>
      {detailItem?.type === 'vendor' && <VendorDetail vendorId={detailItem.id} />}
    </div>
  )
}
