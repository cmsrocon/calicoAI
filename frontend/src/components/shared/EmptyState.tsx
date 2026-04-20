interface Props {
  title: string
  description?: string
  icon?: string
}

export default function EmptyState({ title, description, icon = '🐱' }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
      <span className="text-5xl">{icon}</span>
      <p className="text-stone-300 font-medium">{title}</p>
      {description && <p className="text-stone-500 text-sm max-w-xs">{description}</p>}
    </div>
  )
}
