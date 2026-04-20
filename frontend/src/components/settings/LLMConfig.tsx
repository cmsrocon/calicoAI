import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, ChevronDown, ChevronRight, Eye, EyeOff, XCircle } from 'lucide-react'
import { useState } from 'react'
import { checkHealth, fetchSettings, updateSettings } from '../../api/settings'
import LoadingSpinner from '../shared/LoadingSpinner'

const PROVIDER_KEY_FIELD: Record<string, string> = {
  anthropic: 'anthropic_api_key',
  openai: 'openai_api_key',
  minimax: 'minimax_api_key',
}

const PROVIDER_KEY_HINT: Record<string, string> = {
  anthropic: 'sk-ant-api03-…',
  openai: 'sk-proj-…',
  minimax: 'eyJ…',
}

const PROVIDER_MODELS: Record<string, string[]> = {
  anthropic: ['claude-sonnet-4-6', 'claude-opus-4-7', 'claude-haiku-4-5-20251001'],
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4'],
  minimax: ['MiniMax-Text-01', 'abab6.5s-chat'],
  ollama: ['llama3.2', 'qwen2.5', 'mistral', 'gemma3'],
}

interface HealthStep {
  name: string
  status: 'ok' | 'warning' | 'error'
  detail: string
  latency_ms: number
}

interface HealthResult {
  overall: 'ok' | 'degraded' | 'error'
  provider: string
  model: string
  key_configured: boolean
  steps: HealthStep[]
  total_tokens: number
  tokens_in: number
  tokens_out: number
  estimated_cost_usd: number
  llm_calls: number
  total_latency_ms: number
}

function fmt(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

export default function LLMConfig() {
  const queryClient = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['settings'], queryFn: fetchSettings })
  const [form, setForm] = useState<Record<string, string>>({})
  // Key edits are tracked separately and never pre-populated from settings
  const [keyEdits, setKeyEdits] = useState<Record<string, string>>({})
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})
  const [health, setHealth] = useState<HealthResult | null>(null)
  const [checking, setChecking] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState(false)

  const effective = { ...settings, ...form }
  const provider = effective['llm_provider'] || 'anthropic'
  const keyField = PROVIDER_KEY_FIELD[provider]

  const saveMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, string> = { ...form }
      // Only include key edits if the user actually typed something
      if (keyField && keyEdits[keyField]?.trim()) {
        payload[keyField] = keyEdits[keyField].trim()
      }
      return updateSettings(payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setForm({})
      setKeyEdits({})
    },
  })

  const handleHealth = async () => {
    setChecking(true)
    setHealth(null)
    setExpandedSteps(false)
    try {
      const res = await checkHealth()
      setHealth(res)
      setExpandedSteps(true)
    } finally {
      setChecking(false)
    }
  }

  const hasPendingChanges = Object.keys(form).length > 0 ||
    (keyField ? !!keyEdits[keyField]?.trim() : false)

  // Is a key already saved for this provider?
  const storedKeyMasked = keyField ? (settings?.[keyField] || '') : ''
  const keyIsSaved = storedKeyMasked.length > 0

  const select = (key: string, label: string, options: string[]) => (
    <div key={key}>
      <label className="text-xs text-stone-400 mb-1 block">{label}</label>
      <select
        value={effective[key] || ''}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
      >
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )

  const textField = (key: string, label: string) => (
    <div key={key}>
      <label className="text-xs text-stone-400 mb-1 block">{label}</label>
      <input
        type="text"
        value={effective[key] || ''}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
      />
    </div>
  )

  const stepIcon = (status: HealthStep['status']) => {
    if (status === 'ok') return <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
    if (status === 'warning') return <span className="text-yellow-400 shrink-0 text-xs mt-0.5">⚠</span>
    return <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
  }

  return (
    <div className="space-y-5 max-w-md">
      {/* Provider */}
      {select('llm_provider', 'Provider', ['anthropic', 'openai', 'minimax', 'ollama'])}

      {/* Model — quick-pick suggestions + free text */}
      <div>
        <label className="text-xs text-stone-400 mb-1 block">Model</label>
        <input
          type="text"
          value={effective['llm_model'] || ''}
          onChange={(e) => setForm((f) => ({ ...f, llm_model: e.target.value }))}
          list="model-suggestions"
          className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
        />
        <datalist id="model-suggestions">
          {(PROVIDER_MODELS[provider] || []).map((m) => <option key={m} value={m} />)}
        </datalist>
      </div>

      {/* API key — shown for all providers except Ollama */}
      {keyField && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-stone-400">
              API key
              {keyIsSaved && (
                <span className="ml-2 text-emerald-400">· saved ({storedKeyMasked})</span>
              )}
              {!keyIsSaved && (
                <span className="ml-2 text-red-400">· not set</span>
              )}
            </label>
          </div>
          <div className="relative">
            <input
              type={showKeys[keyField] ? 'text' : 'password'}
              placeholder={keyIsSaved ? 'Enter new key to replace…' : (PROVIDER_KEY_HINT[provider] || 'Paste your API key…')}
              value={keyEdits[keyField] || ''}
              onChange={(e) => setKeyEdits((k) => ({ ...k, [keyField]: e.target.value }))}
              className="w-full bg-stone-900 border border-stone-700 rounded-lg px-3 py-2 pr-10 text-sm text-stone-100 focus:outline-none focus:border-orange-500"
            />
            <button
              type="button"
              onClick={() => setShowKeys((s) => ({ ...s, [keyField]: !s[keyField] }))}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-300"
            >
              {showKeys[keyField] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
          <p className="text-xs text-stone-600 mt-1">
            {provider === 'anthropic' && <>Get yours at console.anthropic.com/settings/keys</>}
            {provider === 'openai' && <>Get yours at platform.openai.com/api-keys</>}
            {provider === 'minimax' && <>Get yours at www.minimaxi.chat — API Keys section</>}
          </p>
        </div>
      )}

      {/* Ollama base URL */}
      {provider === 'ollama' && textField('ollama_base_url', 'Ollama base URL (e.g. http://localhost:11434/v1)')}

      {/* Schedule */}
      <div className="grid grid-cols-2 gap-3">
        {textField('schedule_hour', 'Daily refresh — hour (0–23)')}
        {textField('schedule_minute', 'Minute (0–59)')}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleHealth}
          disabled={checking}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-stone-800 hover:bg-stone-700 text-stone-300 rounded-lg transition-colors disabled:opacity-50"
        >
          {checking ? <LoadingSpinner size="sm" /> : null}
          {checking ? 'Testing…' : 'Test connection'}
        </button>
        {hasPendingChanges && (
          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
            className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save'}
          </button>
        )}
      </div>

      {/* Health result */}
      {health && (
        <div className={`rounded-lg border p-3 space-y-3 ${
          health.overall === 'ok' ? 'border-emerald-800/60 bg-emerald-950/20'
          : health.overall === 'degraded' ? 'border-yellow-800/60 bg-yellow-950/20'
          : 'border-red-800/60 bg-red-950/20'
        }`}>
          {/* Summary row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {health.overall === 'ok'
                ? <CheckCircle className="w-4 h-4 text-emerald-400" />
                : <XCircle className="w-4 h-4 text-red-400" />}
              <span className={`text-sm font-medium ${
                health.overall === 'ok' ? 'text-emerald-400'
                : health.overall === 'degraded' ? 'text-yellow-400'
                : 'text-red-400'
              }`}>
                {health.overall === 'ok' ? 'All checks passed'
                  : health.overall === 'degraded' ? 'Connected with issues'
                  : 'Connection failed'}
              </span>
            </div>
            <span className="text-xs text-stone-500">{health.total_latency_ms}ms total</span>
          </div>

          {/* Stats row */}
          {health.llm_calls > 0 && (
            <div className="flex gap-4 text-xs text-stone-500 font-mono">
              <span>{health.llm_calls} calls</span>
              <span>{fmt(health.tokens_in)} in / {fmt(health.tokens_out)} out</span>
              {health.estimated_cost_usd > 0 && (
                <span className="text-stone-400">${health.estimated_cost_usd.toFixed(4)}</span>
              )}
            </div>
          )}

          {/* Steps toggle */}
          <button
            onClick={() => setExpandedSteps((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-stone-500 hover:text-stone-300 transition-colors"
          >
            {expandedSteps ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            {expandedSteps ? 'Hide' : 'Show'} step details
          </button>

          {expandedSteps && (
            <div className="space-y-2">
              {health.steps.map((step) => (
                <div key={step.name} className="flex items-start gap-2">
                  {stepIcon(step.status)}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-stone-300">{step.name}</span>
                      {step.latency_ms > 0 && (
                        <span className="text-xs text-stone-600 font-mono">{step.latency_ms}ms</span>
                      )}
                    </div>
                    <p className="text-xs text-stone-500 mt-0.5">{step.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
