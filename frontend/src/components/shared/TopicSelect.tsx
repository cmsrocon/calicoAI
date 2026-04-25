import { useQuery } from '@tanstack/react-query'
import { fetchTopics } from '../../api/topics'

interface Props {
  value: number | null
  onChange: (value: number | null) => void
  label?: string
  allLabel?: string
  className?: string
}

export default function TopicSelect({
  value,
  onChange,
  label = 'Topic',
  allLabel = 'All topics',
  className = '',
}: Props) {
  const { data: topics } = useQuery({
    queryKey: ['topics'],
    queryFn: fetchTopics,
  })

  return (
    <div className={className}>
      <label className="text-xs text-stone-500 mb-1 block">{label}</label>
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
      >
        <option value="">{allLabel}</option>
        {topics?.map((topic) => (
          <option key={topic.id} value={topic.id}>
            {topic.name}
          </option>
        ))}
      </select>
    </div>
  )
}
