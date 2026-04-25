import { useQuery } from '@tanstack/react-query'
import { Plus, Settings2, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { fetchTopics } from '../api/topics'
import AddSourceModal from '../components/settings/AddSourceModal'
import AddTopicModal from '../components/settings/AddTopicModal'
import LLMConfig from '../components/settings/LLMConfig'
import SourceTable from '../components/settings/SourceTable'
import type { Topic } from '../types'

export default function SettingsPage() {
  const [settingsTab, setSettingsTab] = useState<'global' | 'topics'>('global')
  const [addingSource, setAddingSource] = useState(false)
  const [addingTopic, setAddingTopic] = useState(false)
  const [activeTopicId, setActiveTopicId] = useState<number | null>(null)
  const { data: topics } = useQuery({
    queryKey: ['topics'],
    queryFn: fetchTopics,
  })

  useEffect(() => {
    if (!topics?.length) return
    if (activeTopicId && topics.some((topic) => topic.id === activeTopicId)) return
    setActiveTopicId(topics[0].id)
  }, [topics, activeTopicId])

  const activeTopic = topics?.find((topic) => topic.id === activeTopicId) ?? null

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex items-center gap-2 border-b border-stone-800">
        <button
          onClick={() => setSettingsTab('global')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            settingsTab === 'global'
              ? 'border-orange-500 text-orange-300'
              : 'border-transparent text-stone-500 hover:text-stone-300'
          }`}
        >
          <span className="inline-flex items-center gap-2">
            <Settings2 className="w-4 h-4" />
            Global Settings
          </span>
        </button>
        <button
          onClick={() => setSettingsTab('topics')}
          className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
            settingsTab === 'topics'
              ? 'border-orange-500 text-orange-300'
              : 'border-transparent text-stone-500 hover:text-stone-300'
          }`}
        >
          <span className="inline-flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Topic Settings
          </span>
        </button>
      </div>

      {settingsTab === 'global' && (
        <section className="max-w-3xl">
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-stone-200">LLM Configuration</h2>
            <p className="text-xs text-stone-500">Provider, model, API keys, and refresh schedule apply to every topic.</p>
          </div>
          <LLMConfig />
        </section>
      )}

      {settingsTab === 'topics' && (
        <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-stone-200">Topics</h2>
                <p className="text-xs text-stone-500">Each topic keeps its own source list and article stream.</p>
              </div>
              <button
                onClick={() => setAddingTopic(true)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add
              </button>
            </div>

            <div className="space-y-2">
              {topics?.map((topic: Topic) => (
                <button
                  key={topic.id}
                  onClick={() => setActiveTopicId(topic.id)}
                  className={`w-full text-left border rounded-xl px-4 py-3 transition-colors ${
                    activeTopicId === topic.id
                      ? 'border-orange-500 bg-orange-950/20'
                      : 'border-stone-800 bg-stone-950 hover:border-stone-700'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-stone-100">{topic.name}</p>
                    {topic.is_default && (
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-stone-800 text-stone-300">Default</span>
                    )}
                  </div>
                  {topic.description && <p className="text-xs text-stone-500 mt-1 line-clamp-2">{topic.description}</p>}
                  <p className="text-[11px] text-stone-600 mt-2">
                    {topic.source_count} sources | {topic.article_count} articles
                  </p>
                </button>
              ))}
            </div>
          </section>

          <section className="space-y-5">
            {activeTopic ? (
              <>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-semibold text-stone-200">{activeTopic.name} Sources</h2>
                    <p className="text-xs text-stone-500">
                      Active sources in this topic are fetched on every refresh run.
                    </p>
                  </div>
                  <button
                    onClick={() => setAddingSource(true)}
                    className="px-4 py-2 text-sm bg-orange-500 hover:bg-orange-400 text-white rounded-lg transition-colors"
                  >
                    Add Source
                  </button>
                </div>

                {activeTopic.description && (
                  <div className="rounded-xl border border-stone-800 bg-stone-950 px-4 py-3">
                    <p className="text-xs font-semibold text-stone-400 uppercase tracking-wide mb-1">Topic Scope</p>
                    <p className="text-sm text-stone-300">{activeTopic.description}</p>
                  </div>
                )}

                <SourceTable topicId={activeTopic.id} />
              </>
            ) : (
              <div className="rounded-xl border border-stone-800 bg-stone-950 px-4 py-8 text-center text-sm text-stone-500">
                Create a topic to start managing its sources.
              </div>
            )}
          </section>
        </div>
      )}

      {addingTopic && (
        <AddTopicModal
          onClose={() => setAddingTopic(false)}
          onCreated={(topicId) => setActiveTopicId(topicId)}
        />
      )}
      {addingSource && activeTopicId && (
        <AddSourceModal topicId={activeTopicId} onClose={() => setAddingSource(false)} />
      )}
    </div>
  )
}
