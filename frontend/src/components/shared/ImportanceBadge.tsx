interface Props {
  rank: number | null
}

export default function ImportanceBadge({ rank }: Props) {
  if (!rank) return null
  const colors = [
    '', // 0
    'bg-stone-700 text-stone-300',  // 1
    'bg-stone-700 text-stone-300',  // 2
    'bg-stone-600 text-stone-200',  // 3
    'bg-stone-600 text-stone-200',  // 4
    'bg-yellow-900 text-yellow-300', // 5
    'bg-yellow-800 text-yellow-200', // 6
    'bg-orange-900 text-orange-300', // 7
    'bg-orange-800 text-orange-200', // 8
    'bg-red-900 text-red-300',       // 9
    'bg-red-800 text-red-200',       // 10
  ]
  return (
    <span className={`text-xs font-bold px-2 py-0.5 rounded-full tabular-nums ${colors[rank] || colors[5]}`}>
      {rank}
    </span>
  )
}
