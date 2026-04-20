import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle } from 'lucide-react'
import { useState } from 'react'
import { checkHealth, fetchSettings, updateSettings } from '../../api/settings'
import LoadingSpinner from '../shared/LoadingSpinner'

export default function LLMConfig() {
  const queryClient = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: fetchSettings })
  const [form, setForm] = useState<Record<string, string>>({})
  const [health, setHealth] = useState<{ status: string; latency_ms?: number; error?: string } | null>(null)
  const [checking, setChecking] = useState(false)

  const effective = { ...settings, ...form }

  const saveMutation = useMutation({
    mutationFn: () => updateSettings(form),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setForm({})
    },
  })

  const handleHealth = async () => {
    setChecking(true)
    setHealth(null)
    try {
      const res = await checkHealth()
      setHealth(res)
    } finally {
      setChecking(false)
    }
  }

  const field = (key: string, label: string, type: 'text' | 'select' = 'text', options?: string[]) => (
    <div key={key}>
      <label className="text-xs text-stone-400 mb-1 block">{label}</label>
      {type === 'select' ? (
        <select
          value={effective[key] || ''}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        >
          {options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      ) : (
        <input
          type="text"
          value={effective[key] || ''}
          onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        />
      )}
    </div>
  )

  return (
    <div className="space-y-4 max-w-md">
      {field('llm_provider', 'Provider', 'select', ['anthropic', 'openai', 'minimax', 'ollama'])}
      {field('llm_model', 'Model name')}
      {effective['llm_provider'] === 'ollama' && field('ollama_base_url', 'Ollama base URL (e.g. http://192.168.1.50:11434/v1)')}
      {field('schedule_hour', 'Daily refresh hour (0–23)')}
      {field('schedule_minute', 'Daily refresh minute (0–59)')}

      <div className="flex gap-2">
        <button
          onClick={handleHealth}
          disabled={checking}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-stone-800 hover:bg-stone-700 text-stone-300 rounded-lg transition-colors disabled:opacity-50"
        >
          {checking ? <LoadingSpinner size="sm" /> : null}
          Test connection
        </button>
        {Object.keys(form).length > 0 && (
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>

      {health && (
        <div className={`flex items-center gap-2 text-sm ${health.status === 'ok' ? 'text-emerald-400' : 'text-red-400'}`}>
          {health.status === 'ok'
            ? <><CheckCircle className="w-4 h-4" /> Connected ({health.latency_ms}ms)</>
            : <><XCircle className="w-4 h-4" /> {health.error}</>}
        </div>
      )}
    </div>
  )
}
