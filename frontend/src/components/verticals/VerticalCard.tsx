import { Layers } from 'lucide-react'
import type { Vertical } from '../../types'

interface Props {
  vertical: Vertical
  onClick: () => void
}

export default function VerticalCard({ vertical, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left border border-stone-800 rounded-xl p-4 hover:border-blue-700 hover:bg-stone-900 transition-colors group"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-stone-800 group-hover:bg-blue-950 transition-colors">
          <Layers className="w-4 h-4 text-stone-400 group-hover:text-blue-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-stone-100 group-hover:text-blue-300 transition-colors">{vertical.name}</p>
          <p className="text-xs text-stone-600 mt-0.5">{vertical.news_count} articles</p>
        </div>
      </div>
    </button>
  )
}
