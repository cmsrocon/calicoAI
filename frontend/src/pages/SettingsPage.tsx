import { useState } from 'react'
import AddSourceModal from '../components/settings/AddSourceModal'
import LLMConfig from '../components/settings/LLMConfig'
import SourceTable from '../components/settings/SourceTable'

export default function SettingsPage() {
  const [addingSource, setAddingSource] = useState(false)

  return (
    <div className="max-w-3xl space-y-10">
      <section>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-stone-200">Trusted Sources</h2>
            <p className="text-xs text-stone-500">Active sources are fetched on each refresh</p>
          </div>
          <button
            onClick={() => setAddingSource(true)}
            className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg transition-colors"
          >
            Add Source
          </button>
        </div>
        <SourceTable />
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-stone-200">LLM Configuration</h2>
          <p className="text-xs text-stone-500">Provider and model used for analysis. Changes take effect on next ingestion.</p>
        </div>
        <LLMConfig />
      </section>

      {addingSource && <AddSourceModal onClose={() => setAddingSource(false)} />}
    </div>
  )
}
