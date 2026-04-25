import { ThumbsDown, ThumbsUp, Scale } from 'lucide-react'

interface Props {
  pros: string[]
  cons: string[]
  balancedTake: string | null
}

export default function BalancedTake({ pros, cons, balancedTake }: Props) {
  if (!pros.length && !cons.length && !balancedTake) return null
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        {pros.length > 0 && (
          <div className="bg-emerald-950/40 border border-emerald-900 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <ThumbsUp className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">Pros</span>
            </div>
            <ul className="space-y-1">
              {pros.map((p, i) => (
                <li key={i} className="text-xs text-emerald-200">· {p}</li>
              ))}
            </ul>
          </div>
        )}
        {cons.length > 0 && (
          <div className="bg-red-950/40 border border-red-900 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <ThumbsDown className="w-3.5 h-3.5 text-red-400" />
              <span className="text-xs font-semibold text-red-400 uppercase tracking-wide">Cons</span>
            </div>
            <ul className="space-y-1">
              {cons.map((c, i) => (
                <li key={i} className="text-xs text-red-200">· {c}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {balancedTake && (
        <div className="bg-stone-900 border border-stone-700 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-2">
            <Scale className="w-3.5 h-3.5 text-orange-400" />
            <span className="text-xs font-semibold text-orange-400 uppercase tracking-wide">Balanced view</span>
          </div>
          <p className="text-xs text-stone-300 leading-relaxed">{balancedTake}</p>
        </div>
      )}
    </div>
  )
}
