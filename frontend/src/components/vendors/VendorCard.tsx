import { Building2 } from 'lucide-react'
import type { VendorSummary } from '../../types'

interface Props {
  vendor: VendorSummary
  onClick: () => void
}

export default function VendorCard({ vendor, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left border border-stone-800 rounded-xl p-4 hover:border-orange-700 hover:bg-stone-900 transition-colors group"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-stone-800 group-hover:bg-orange-950 transition-colors">
          <Building2 className="w-4 h-4 text-stone-400 group-hover:text-orange-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-stone-100 group-hover:text-orange-300 transition-colors truncate">{vendor.name}</p>
          {vendor.description && (
            <p className="text-xs text-stone-500 mt-0.5 line-clamp-2">{vendor.description}</p>
          )}
          <p className="text-xs text-stone-600 mt-1">{vendor.news_count} articles</p>
        </div>
      </div>
    </button>
  )
}
