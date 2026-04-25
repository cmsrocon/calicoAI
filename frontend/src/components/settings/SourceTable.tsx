import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, FlaskConical, Trash2, XCircle } from 'lucide-react'
import { useState } from 'react'
import { deleteSource, fetchSources, testSource, updateSource } from '../../api/sources'
import type { Source } from '../../types'
import LoadingSpinner from '../shared/LoadingSpinner'

export default function SourceTable({ topicId }: { topicId: number }) {
  const queryClient = useQueryClient()
  const { data: sources, isLoading } = useQuery({
    queryKey: ['sources', topicId],
    queryFn: () => fetchSources(topicId),
    enabled: !!topicId,
  })
  const [testing, setTesting] = useState<number | null>(null)
  const [testResult, setTestResult] = useState<{ id: number; msg: string } | null>(null)

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) => updateSource(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources', topicId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteSource,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources', topicId] })
      queryClient.invalidateQueries({ queryKey: ['topics'] })
    },
  })

  const handleTest = async (source: Source) => {
    setTesting(source.id)
    setTestResult(null)
    try {
      const res = await testSource(source.id)
      setTestResult({
        id: source.id,
        msg: res.success
          ? `Found ${res.item_count} items${res.sample_title ? `: "${res.sample_title.slice(0, 60)}..."` : ''}`
          : `Error: ${res.error}`,
      })
    } finally {
      setTesting(null)
    }
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-2">
      {sources?.map((source) => (
        <div key={source.id} className="border border-stone-800 rounded-xl p-3 flex items-start gap-3">
          <button onClick={() => toggleMutation.mutate({ id: source.id, is_active: !source.is_active })} className="shrink-0 mt-0.5">
            {source.is_active ? (
              <CheckCircle className="w-5 h-5 text-emerald-500" />
            ) : (
              <XCircle className="w-5 h-5 text-stone-600" />
            )}
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-medium text-stone-200">{source.name}</p>
              <span className="text-xs px-1.5 py-0.5 rounded bg-stone-800 text-stone-500">{source.feed_type}</span>
              <span className="text-xs text-stone-600">trust {source.trust_weight.toFixed(1)}</span>
            </div>
            <p className="text-xs text-stone-600 truncate">{source.url}</p>
            {source.last_error && <p className="text-xs text-red-400 mt-0.5">{source.last_error}</p>}
            {testResult?.id === source.id && <p className="text-xs text-orange-300 mt-0.5">{testResult.msg}</p>}
          </div>
          <div className="flex gap-1 shrink-0">
            <button
              onClick={() => handleTest(source)}
              disabled={testing === source.id}
              className="p-1.5 rounded-lg text-stone-500 hover:text-orange-400 hover:bg-stone-800 transition-colors disabled:opacity-50"
            >
              {testing === source.id ? <LoadingSpinner size="sm" /> : <FlaskConical className="w-4 h-4" />}
            </button>
            <button
              onClick={() => {
                if (confirm(`Delete "${source.name}"?`)) deleteMutation.mutate(source.id)
              }}
              className="p-1.5 rounded-lg text-stone-600 hover:text-red-400 hover:bg-stone-800 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
      {sources?.length === 0 && (
        <div className="rounded-xl border border-stone-800 bg-stone-950 px-4 py-8 text-center text-sm text-stone-500">
          No sources yet for this topic.
        </div>
      )}
    </div>
  )
}
