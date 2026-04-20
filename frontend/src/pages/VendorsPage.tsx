import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchVendors } from '../api/vendors'
import VendorCard from '../components/vendors/VendorCard'
import VendorDetail from '../components/vendors/VendorDetail'
import EmptyState from '../components/shared/EmptyState'
import LoadingSpinner from '../components/shared/LoadingSpinner'
import SearchBar from '../components/shared/SearchBar'
import { useUIStore } from '../store/uiStore'

export default function VendorsPage() {
  const [search, setSearch] = useState('')
  const { data, isLoading } = useQuery({
    queryKey: ['vendors', { search }],
    queryFn: () => fetchVendors(search),
  })
  const { detailItem, openDetail } = useUIStore()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-stone-200">AI Vendors</h2>
        {data && <span className="text-xs text-stone-500">{data.total} tracked</span>}
      </div>
      <SearchBar placeholder="Search vendors…" value={search} onChange={setSearch} />
      {isLoading && <div className="flex justify-center py-12"><LoadingSpinner size="lg" /></div>}
      {!isLoading && !data?.vendors.length && (
        <EmptyState title="No vendors yet" description="Vendors are discovered automatically during ingestion" icon="🏢" />
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {data?.vendors.map((v: { id: number; name: string; slug: string; description: string | null; news_count: number }) => (
          <VendorCard key={v.id} vendor={v} onClick={() => openDetail('vendor', v.id)} />
        ))}
      </div>
      {detailItem?.type === 'vendor' && <VendorDetail vendorId={detailItem.id} />}
    </div>
  )
}
