import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { useState } from 'react'
import { createSource } from '../../api/sources'

interface Props {
  topicId: number
  onClose: () => void
}

export default function AddSourceModal({ topicId, onClose }: Props) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ topic_id: topicId, name: '', url: '', feed_type: 'rss', trust_weight: 1.0 })

  const mutation = useMutation({
    mutationFn: () => createSource(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', topicId] })
      queryClient.invalidateQueries({ queryKey: ['topics'] })
      onClose()
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative bg-stone-900 border border-stone-700 rounded-2xl p-6 w-full max-w-md space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-stone-100">Add Source</h3>
          <button onClick={onClose} className="text-stone-500 hover:text-stone-200">
            <X className="w-4 h-4" />
          </button>
        </div>

        {['name', 'url'].map((field) => (
          <div key={field}>
            <label className="text-xs text-stone-400 mb-1 block capitalize">{field}</label>
            <input
              type="text"
              value={form[field as keyof typeof form] as string}
              onChange={(e) => setForm((current) => ({ ...current, [field]: e.target.value }))}
              className="w-full bg-stone-800 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
            />
          </div>
        ))}

        <div>
          <label className="text-xs text-stone-400 mb-1 block">Feed type</label>
          <select
            value={form.feed_type}
            onChange={(e) => setForm((current) => ({ ...current, feed_type: e.target.value }))}
            className="w-full bg-stone-800 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
          >
            <option value="rss">RSS</option>
            <option value="html">HTML</option>
          </select>
        </div>

        <div>
          <label className="text-xs text-stone-400 mb-1 block">Trust weight: {form.trust_weight.toFixed(1)}</label>
          <input
            type="range"
            min={0.5}
            max={2.0}
            step={0.1}
            value={form.trust_weight}
            onChange={(e) => setForm((current) => ({ ...current, trust_weight: Number(e.target.value) }))}
            className="w-full accent-orange-500"
          />
        </div>

        {mutation.isError && <p className="text-xs text-red-400">{(mutation.error as Error).message}</p>}

        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-stone-400 hover:text-stone-200 transition-colors">
            Cancel
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={!form.name || !form.url || mutation.isPending}
            className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg disabled:opacity-50 transition-colors"
          >
            {mutation.isPending ? 'Adding...' : 'Add Source'}
          </button>
        </div>
      </div>
    </div>
  )
}
