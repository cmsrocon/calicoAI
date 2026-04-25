import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useState } from 'react'
import { createTopic } from '../../api/topics'

interface Props {
  onClose: () => void
  onCreated: (topicId: number) => void
}

export default function AddTopicModal({ onClose, onCreated }: Props) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ name: '', description: '' })
  const [seedResult, setSeedResult] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => createTopic({ name: form.name, description: form.description || undefined }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      setSeedResult(
        result.seed_status === 'ok'
          ? `Seeded ${result.seeded_sources_count} starter sources for ${result.topic.name}.`
          : result.seed_message || 'The topic was created, but no starter sources were seeded.'
      )
      window.setTimeout(() => {
        onCreated(result.topic.id)
        onClose()
      }, 900)
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-stone-900 border border-stone-700 rounded-2xl p-6 w-full max-w-lg space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-stone-100">Add Topic</h3>
          <button onClick={onClose} className="text-stone-500 hover:text-stone-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div>
          <label className="text-xs text-stone-400 mb-1 block">Name</label>
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
            placeholder="Politics, Sport, Climate..."
            className="w-full bg-stone-800 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
          />
        </div>

        <div>
          <label className="text-xs text-stone-400 mb-1 block">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))}
            rows={4}
            placeholder="Optional guidance for relevance scoring and source seeding."
            className="w-full bg-stone-800 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500 resize-none"
          />
        </div>

        <div className="rounded-xl border border-stone-800 bg-stone-950/60 px-3 py-2">
          <p className="text-xs text-stone-400">
            calicoAI will ask the configured model to seed a starter source list for the new topic automatically.
          </p>
        </div>

        {seedResult && <p className="text-xs text-emerald-300">{seedResult}</p>}
        {mutation.isError && <p className="text-xs text-red-400">{(mutation.error as Error).message}</p>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-stone-400 hover:text-stone-200 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.name.trim() || mutation.isPending}
            className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Creating...' : 'Create Topic'}
          </button>
        </div>
      </div>
    </div>
  )
}
