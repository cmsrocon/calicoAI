import { useQueryClient } from '@tanstack/react-query'
import { RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchIngestionStatus, triggerIngestion } from '../../api/ingestion'
import type { IngestionStatus } from '../../types'
import LoadingSpinner from '../shared/LoadingSpinner'

export default function StatusBar() {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState<IngestionStatus | null>(null)
  const [triggering, setTriggering] = useState(false)

  const loadStatus = async () => {
    try {
      const s = await fetchIngestionStatus()
      setStatus(s)
      if (s.is_running) {
        setTimeout(loadStatus, 5000)
      } else if (triggering) {
        setTriggering(false)
        queryClient.invalidateQueries()
      }
    } catch {
      // silent
    }
  }

  useEffect(() => { loadStatus() }, [])

  const handleRefresh = async () => {
    if (triggering || status?.is_running) return
    setTriggering(true)
    try {
      await triggerIngestion()
      setTimeout(loadStatus, 1000)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      alert(err?.response?.data?.detail || 'Failed to start ingestion')
      setTriggering(false)
    }
  }

  const lastRun = status?.last_run
  const isRunning = status?.is_running || triggering

  return (
    <div className="flex items-center gap-4 text-xs text-stone-500">
      {lastRun && (
        <span>
          Last run: <span className={lastRun.status === 'success' ? 'text-emerald-400' : lastRun.status === 'failed' ? 'text-red-400' : 'text-yellow-400'}>
            {lastRun.status}
          </span>
          {lastRun.finished_at && (
            <> · {new Date(lastRun.finished_at).toLocaleTimeString()}</>
          )}
          {lastRun.items_new > 0 && <> · +{lastRun.items_new} new</>}
        </span>
      )}
      <button
        onClick={handleRefresh}
        disabled={isRunning}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-stone-800 hover:bg-stone-700 text-stone-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isRunning ? (
          <><LoadingSpinner size="sm" /> Running…</>
        ) : (
          <><RefreshCw className="w-3 h-3" /> Refresh</>
        )}
      </button>
    </div>
  )
}
