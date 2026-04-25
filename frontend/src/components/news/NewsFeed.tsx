import { useQuery } from '@tanstack/react-query'
import { fetchNews } from '../../api/news'
import { useFilterStore } from '../../store/filterStore'
import EmptyState from '../shared/EmptyState'
import LoadingSpinner from '../shared/LoadingSpinner'
import NewsCard from './NewsCard'

export default function NewsFeed() {
  const filters = useFilterStore()
  const queryFilters = {
    topic_id: filters.selectedTopicId || undefined,
    search: filters.search || undefined,
    sort_by: filters.sortBy,
    min_importance: filters.minImportance || undefined,
    date_from: filters.dateFrom || undefined,
    date_to: filters.dateTo || undefined,
    vendor_id: filters.vendorIds[0] || undefined,
    vertical_id: filters.verticalIds[0] || undefined,
    page_size: 50,
  }

  const { data, isLoading, isError } = useQuery({
    queryKey: ['news', queryFilters],
    queryFn: () => fetchNews(queryFilters),
  })

  if (isLoading) return <div className="flex justify-center py-24"><LoadingSpinner size="lg" /></div>
  if (isError) return <EmptyState title="Failed to load news" description="Check the backend is running" icon="⚠️" />
  if (!data?.items.length) return (
    <EmptyState
      title="No news items yet"
      description="Click Refresh in the top bar to ingest from your trusted sources"
    />
  )

  return (
    <div className="space-y-2">
      <p className="text-xs text-stone-500">
        {data.total} items{filters.selectedTopicId ? ' in selected topic' : ' across all topics'}
      </p>
      {data.items.map((item) => (
        <NewsCard key={item.id} item={item} />
      ))}
    </div>
  )
}
