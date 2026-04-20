interface Props {
  label: string
  color?: 'orange' | 'blue' | 'green'
  onClick?: () => void
}

export default function TagChip({ label, color = 'orange', onClick }: Props) {
  const colors = {
    orange: 'bg-orange-950 text-orange-300 border-orange-800 hover:bg-orange-900',
    blue: 'bg-blue-950 text-blue-300 border-blue-800 hover:bg-blue-900',
    green: 'bg-emerald-950 text-emerald-300 border-emerald-800 hover:bg-emerald-900',
  }
  return (
    <span
      onClick={onClick}
      className={`inline-flex items-center text-xs px-2 py-0.5 rounded border ${colors[color]} ${onClick ? 'cursor-pointer' : ''} transition-colors`}
    >
      {label}
    </span>
  )
}
