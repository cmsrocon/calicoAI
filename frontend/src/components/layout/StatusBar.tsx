import { useQueryClient } from '@tanstack/react-query'
import { Loader2, RefreshCw, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { fetchIngestionStatus, triggerIngestion } from '../../api/ingestion'
import type { IngestionStatus } from '../../types'

function fmt(n: number): string {
  return n >= 1_000_000 ? `${(n / 1_000_000).toFixed(2)}M`
    : n >= 1_000 ? `${(n / 1_000).toFixed(1)}k`
    : String(n)
}

function fmtCost(usd: number): string {
  if (usd < 0.001) return '<$0.001'
  if (usd < 0.01) return `$${usd.toFixed(4)}`
  return `$${usd.toFixed(3)}`
}

export default function StatusBar() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [isTriggering, setIsTriggering] = useState(false)
  const [showProgress, setShowProgress] = useState(false)

  const isRunningRef = useRef(false)
  const pollRef = useRef<() => Promise<void>>()

  pollRef.current = async () => {
    try {
      const s = await fetchIngestionStatus()
      setStatus(s)
      if (s.is_running) {
        setTimeout(() => pollRef.current?.(), 3000)
      } else if (isRunningRef.current) {
        isRunningRef.current = false
        setIsTriggering(false)
        setShowProgress(false)
        queryClient.invalidateQueries()
      }
    } catch {
      // silent
    }
  }

  useEffect(() => { pollRef.current?.() }, [])

  const handleRefresh = async () => {
    if (isTriggering || status?.is_running) return
    setIsTriggering(true)
    isRunningRef.current = true
    try {
      await triggerIngestion()
      setShowProgress(true)
      setTimeout(() => pollRef.current?.(), 1000)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || 'Failed to start ingestion')
      isRunningRef.current = false
      setIsTriggering(false)
    }
  }

  const lastRun = status?.last_run
  const isRunning = status?.is_running || isTriggering

  const liveTokens = (status?.live_tokens_in ?? 0) + (status?.live_tokens_out ?? 0)

  return (
    <div className="flex items-center gap-4 text-xs text-stone-500">
      {lastRun && (
        <span className="flex items-center gap-1.5 flex-wrap">
          <span>
            Last:{' '}
            <span className={
              lastRun.status === 'success' ? 'text-emerald-400'
              : lastRun.status === 'failed' ? 'text-red-400'
              : 'text-yellow-400'
            }>
              {lastRun.status}
            </span>
          </span>
          {lastRun.finished_at && (
            <span>· {new Date(lastRun.finished_at).toLocaleTimeString()}</span>
          )}
          {lastRun.items_new > 0 && <span>· +{lastRun.items_new} new</span>}
          {lastRun.llm_calls > 0 && (
            <span className="text-stone-600">
              · {lastRun.llm_calls} calls
            </span>
          )}
          {lastRun.estimated_cost_usd != null && lastRun.estimated_cost_usd > 0 && (
            <span className="text-stone-600">· {fmtCost(lastRun.estimated_cost_usd)}</span>
          )}
        </span>
      )}

      {isRunning ? (
        <div className="relative">
          <button
            onClick={() => setShowProgress((v) => !v)}
            title="Click to see current stage"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-stone-800 hover:bg-stone-700 text-orange-400 transition-colors"
          >
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Running…</span>
            {liveTokens > 0 && (
              <span className="text-stone-500 font-mono">{fmt(liveTokens)} tok</span>
            )}
          </button>

          {showProgress && (
            <div className="absolute right-0 top-full mt-1 w-96 bg-stone-900 border border-stone-700 rounded-lg p-4 z-50 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-stone-200">Ingestion progress</p>
                <button onClick={() => setShowProgress(false)} className="text-stone-600 hover:text-stone-300">
                  <X className="w-3 h-3" />
                </button>
              </div>

              {/* Stage */}
              <div>
                {status?.current_stage ? (
                  <>
                    <p className="text-xs font-medium text-orange-400">{status.current_stage}</p>
                    {status.current_stage_detail && (
                      <p className="text-xs text-stone-400 mt-0.5">{status.current_stage_detail}</p>
                    )}
                  </>
                ) : (
                  <p className="text-xs text-stone-500">Starting up…</p>
                )}
              </div>

              {/* Live stats */}
              {(status?.live_calls != null && status.live_calls > 0) && (
                <div className="border-t border-stone-800 pt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
                  <div>
                    <p className="text-stone-600 text-xs">LLM calls</p>
                    <p className="text-stone-300 text-xs font-mono">{status.live_calls}</p>
                  </div>
                  <div>
                    <p className="text-stone-600 text-xs">Est. cost</p>
                    <p className="text-orange-300 text-xs font-mono">
                      {status.live_cost_usd != null ? fmtCost(status.live_cost_usd) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-stone-600 text-xs">Tokens in</p>
                    <p className="text-stone-300 text-xs font-mono">
                      {status.live_tokens_in != null ? fmt(status.live_tokens_in) : '—'}
                    </p>
                  </div>
                  <div>
                    <p className="text-stone-600 text-xs">Tokens out</p>
                    <p className="text-stone-300 text-xs font-mono">
                      {status.live_tokens_out != null ? fmt(status.live_tokens_out) : '—'}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-stone-800 hover:bg-stone-700 text-stone-300 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      )}
    </div>
  )
}
