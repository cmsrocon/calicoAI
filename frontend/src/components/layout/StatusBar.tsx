import { useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Loader2, RefreshCw, X } from 'lucide-react'
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

type RefreshProblem = {
  summary: string
  guidance: string
  raw?: string
}

type ProgressSnapshot = {
  label: string
  percent: number
  detail: string | null
  counts: string | null
}

const STAGES = [
  'Fetching articles',
  'Deduplicating',
  'Semantic deduplication',
  'Filtering for relevance',
  'AI analysis',
  'Completing incomplete articles',
  'Analysing trends',
  'Finalising',
] as const

function describeRefreshProblem(message?: string | null, statusCode?: number): RefreshProblem {
  const normalized = (message || '').trim()
  const lower = normalized.toLowerCase()

  if (statusCode === 409 || lower.includes('already running')) {
    return {
      summary: 'A refresh is already in progress.',
      guidance: 'The current run is still active. Open the progress panel to see what it is doing.',
    }
  }

  if (!normalized) {
    return {
      summary: 'The app could not reach the backend.',
      guidance: 'Make sure the backend server is running, then try Refresh again.',
    }
  }

  if (lower.includes('api key') || lower.includes('authentication') || lower.includes('401') || lower.includes('invalid_api_key')) {
    return {
      summary: 'The configured LLM API key is missing or invalid.',
      guidance: 'Open Settings, confirm the provider, add a valid API key, run Test connection, then try Refresh again.',
      raw: normalized,
    }
  }

  if (lower.includes('model not found') || lower.includes('does not exist') || lower.includes('no model is configured')) {
    return {
      summary: 'The selected model is not configured correctly.',
      guidance: 'Open Settings, choose a supported model for the current provider, run Test connection, then try Refresh again.',
      raw: normalized,
    }
  }

  if (
    lower.includes('expecting value') ||
    lower.includes('invalid json') ||
    lower.includes('empty response') ||
    lower.includes('non-json')
  ) {
    return {
      summary: 'The configured model did not return usable JSON.',
      guidance: 'Open Settings, run Test connection, and switch to a model/provider that passes the JSON check before refreshing again.',
      raw: normalized,
    }
  }

  if (
    lower.includes('connection') ||
    lower.includes('connect') ||
    lower.includes('timeout') ||
    lower.includes('network')
  ) {
    return {
      summary: 'The app could not reach a required API endpoint.',
      guidance: 'Check your network, confirm the provider endpoint is reachable, then run Test connection and try Refresh again.',
      raw: normalized,
    }
  }

  if (lower.includes('database is locked')) {
    return {
      summary: 'The local database is busy.',
      guidance: 'Another backend process or a stuck write is holding the SQLite file. Restart the backend and try Refresh again.',
      raw: normalized,
    }
  }

  return {
    summary: 'Refresh failed.',
    guidance: 'Open Settings, run Test connection, then try Refresh again. If it still fails, use the message below to diagnose the provider issue.',
    raw: normalized,
  }
}

function parseStageCounts(detail?: string | null): { done: number, total: number } | null {
  if (!detail) return null
  const match = detail.match(/(\d+)\s*\/\s*(\d+)/)
  if (!match) return null
  const done = Number(match[1])
  const total = Number(match[2])
  if (!Number.isFinite(done) || !Number.isFinite(total) || total <= 0) return null
  return { done, total }
}

function getProgressSnapshot(status: IngestionStatus | null, isTriggering: boolean): ProgressSnapshot | null {
  if (!status?.is_running && !isTriggering) return null

  const stage = status?.current_stage || 'Starting ingestion'
  const detail = status?.current_stage_detail || null
  const stageIndex = Math.max(STAGES.indexOf(stage as typeof STAGES[number]), 0)
  const stageBase = stageIndex / STAGES.length
  const stageWeight = 1 / STAGES.length
  const counts = parseStageCounts(detail)

  let percent = Math.round(stageBase * 100)
  if (counts) {
    percent = Math.round((stageBase + (counts.done / counts.total) * stageWeight) * 100)
  } else if (stage === 'Starting ingestion' || isTriggering) {
    percent = Math.max(percent, 3)
  } else {
    percent = Math.max(percent, Math.round((stageBase + stageWeight * 0.35) * 100))
  }

  const clampedPercent = Math.max(1, Math.min(percent, 99))
  return {
    label: stage,
    percent: clampedPercent,
    detail,
    counts: counts ? `${counts.done}/${counts.total}` : null,
  }
}

export default function StatusBar() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [isTriggering, setIsTriggering] = useState(false)
  const [showProgress, setShowProgress] = useState(false)
  const [refreshProblem, setRefreshProblem] = useState<RefreshProblem | null>(null)

  const isRunningRef = useRef(false)
  const pollTimeoutRef = useRef<number | null>(null)
  const pollRef = useRef<() => Promise<void>>(async () => {})

  const schedulePoll = (delayMs: number) => {
    if (pollTimeoutRef.current != null) {
      window.clearTimeout(pollTimeoutRef.current)
    }
    pollTimeoutRef.current = window.setTimeout(() => {
      void pollRef.current()
    }, delayMs)
  }

  pollRef.current = async () => {
    try {
      const s = await fetchIngestionStatus()
      setStatus(s)

      if (s.is_running) {
        isRunningRef.current = true
        schedulePoll(2000)
      } else if (isRunningRef.current) {
        isRunningRef.current = false
        setIsTriggering(false)
        if (s.last_error) {
          setRefreshProblem(describeRefreshProblem(s.last_error))
          setShowProgress(true)
        } else if (s.last_run?.status === 'failed') {
          setRefreshProblem(describeRefreshProblem(s.last_run.error_message))
          setShowProgress(true)
        } else {
          setRefreshProblem(null)
          setShowProgress(false)
        }
        queryClient.invalidateQueries()
      }
    } catch (e: unknown) {
      const err = e as { response?: { status?: number, data?: { detail?: string } }, message?: string }
      setRefreshProblem(describeRefreshProblem(err?.response?.data?.detail || err?.message, err?.response?.status))
      if (isRunningRef.current) {
        isRunningRef.current = false
        setIsTriggering(false)
        setShowProgress(true)
      }
    }
  }

  useEffect(() => {
    void pollRef.current()
    return () => {
      if (pollTimeoutRef.current != null) {
        window.clearTimeout(pollTimeoutRef.current)
      }
    }
  }, [])

  const handleRefresh = async () => {
    if (isTriggering || status?.is_running) {
      setShowProgress(true)
      void pollRef.current()
      return
    }

    setIsTriggering(true)
    setShowProgress(true)
    setRefreshProblem(null)
    isRunningRef.current = true

    try {
      await triggerIngestion()
      schedulePoll(800)
    } catch (e: unknown) {
      const err = e as { response?: { status?: number, data?: { detail?: string } }, message?: string }
      const problem = describeRefreshProblem(err?.response?.data?.detail || err?.message, err?.response?.status)

      if (err?.response?.status === 409) {
        setRefreshProblem(null)
        isRunningRef.current = true
        setIsTriggering(false)
        setShowProgress(true)
        await pollRef.current()
        return
      }

      setRefreshProblem(problem)
      setShowProgress(true)
      isRunningRef.current = false
      setIsTriggering(false)
    }
  }

  const lastRun = status?.last_run
  const isRunning = status?.is_running || isTriggering
  const liveTokens = (status?.live_tokens_in ?? 0) + (status?.live_tokens_out ?? 0)
  const progress = getProgressSnapshot(status, isTriggering)

  return (
    <div className="flex flex-col items-end gap-2 text-xs text-stone-500">
      <div className="flex items-center gap-4">
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
              <span className="text-stone-600">· {lastRun.llm_calls} calls</span>
            )}
            {lastRun.estimated_cost_usd != null && lastRun.estimated_cost_usd > 0 && (
              <span className="text-stone-600">· {fmtCost(lastRun.estimated_cost_usd)}</span>
            )}
          </span>
        )}

        <div className="relative">
          <button
            onClick={handleRefresh}
            title={isRunning ? 'Show live ingestion progress' : 'Start a refresh run'}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors ${
              isRunning
                ? 'bg-stone-800 hover:bg-stone-700 text-orange-400'
                : 'bg-stone-800 hover:bg-stone-700 text-stone-300'
            }`}
          >
            {isRunning ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            <span>{isRunning ? 'Running' : 'Refresh'}</span>
            {progress && (
              <span className="text-stone-400">{progress.percent}%</span>
            )}
            <ChevronDown className={`w-3 h-3 text-stone-500 transition-transform ${showProgress ? 'rotate-180' : ''}`} />
          </button>

          {showProgress && (isRunning || refreshProblem) && (
            <div className="absolute right-0 top-full mt-1 w-[26rem] bg-stone-900 border border-stone-700 rounded-lg p-4 z-50 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-stone-200">
                  {isRunning ? 'Ingestion progress' : 'Refresh status'}
                </p>
                <button onClick={() => setShowProgress(false)} className="text-stone-600 hover:text-stone-300">
                  <X className="w-3 h-3" />
                </button>
              </div>

              {isRunning && progress && (
                <>
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-xs font-medium text-orange-400">{progress.label}</p>
                      <p className="text-xs text-stone-400 font-mono">{progress.percent}%</p>
                    </div>
                    <div className="h-2 rounded-full bg-stone-800 overflow-hidden">
                      <div
                        className="h-full bg-orange-500 transition-all duration-500"
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                    {progress.detail && (
                      <p className="text-xs text-stone-400">{progress.detail}</p>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-stone-800 pt-3">
                    <div>
                      <p className="text-stone-600 text-xs">Stage progress</p>
                      <p className="text-stone-300 text-xs font-mono">{progress.counts || 'In progress'}</p>
                    </div>
                    <div>
                      <p className="text-stone-600 text-xs">LLM calls</p>
                      <p className="text-stone-300 text-xs font-mono">
                        {status?.live_calls != null ? status.live_calls : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-600 text-xs">Tokens</p>
                      <p className="text-stone-300 text-xs font-mono">
                        {liveTokens > 0 ? fmt(liveTokens) : '-'}
                      </p>
                    </div>
                    <div>
                      <p className="text-stone-600 text-xs">Est. cost</p>
                      <p className="text-orange-300 text-xs font-mono">
                        {status?.live_cost_usd != null ? fmtCost(status.live_cost_usd) : '-'}
                      </p>
                    </div>
                  </div>
                </>
              )}

              {refreshProblem && (
                <div className="rounded-lg border border-red-900/60 bg-red-950/30 px-3 py-2 text-left">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold text-red-300">{refreshProblem.summary}</p>
                    <p className="text-xs text-red-100/80">{refreshProblem.guidance}</p>
                    {refreshProblem.raw && (
                      <p className="text-xs text-stone-500 font-mono break-words">{refreshProblem.raw}</p>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
