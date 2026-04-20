import { useUIStore } from '../../store/uiStore'
import NewsPage from '../../pages/NewsPage'
import VendorsPage from '../../pages/VendorsPage'
import VerticalsPage from '../../pages/VerticalsPage'
import SettingsPage from '../../pages/SettingsPage'
import TabBar from './TabBar'
import StatusBar from './StatusBar'

export default function Shell() {
  const { activeTab } = useUIStore()

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-stone-800 bg-stone-950 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/ginger-cat.svg" alt="GingerAI" className="w-10 h-10" />
            <div>
              <h1 className="text-lg font-bold text-orange-400 leading-tight">GingerAI</h1>
              <p className="text-xs text-stone-500 leading-tight">AI landscape monitor</p>
            </div>
          </div>
          <TabBar />
          <StatusBar />
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {activeTab === 'news' && <NewsPage />}
        {activeTab === 'vendors' && <VendorsPage />}
        {activeTab === 'verticals' && <VerticalsPage />}
        {activeTab === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
