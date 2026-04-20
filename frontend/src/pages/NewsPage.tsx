import NewsFeed from '../components/news/NewsFeed'
import NewsFilters from '../components/news/NewsFilters'
import NewsDetail from '../components/news/NewsDetail'
import SearchBar from '../components/shared/SearchBar'
import { useFilterStore } from '../store/filterStore'
import { useUIStore } from '../store/uiStore'

export default function NewsPage() {
  const { search, setFilter } = useFilterStore()
  const { detailItem, closeDetail } = useUIStore()

  return (
    <div className="flex gap-6">
      {/* Sidebar */}
      <aside className="w-56 shrink-0">
        <NewsFilters />
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 space-y-4">
        <SearchBar
          placeholder="Search headlines…"
          value={search}
          onChange={(v) => setFilter('search', v)}
        />
        <NewsFeed />
      </div>

      {detailItem?.type === 'news' && <NewsDetail itemId={detailItem.id} />}
    </div>
  )
}
