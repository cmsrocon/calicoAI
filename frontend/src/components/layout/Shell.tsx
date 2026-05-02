import { useUIStore } from '../../store/uiStore'
import NewsPage from '../../pages/NewsPage'
import VendorsPage from '../../pages/VendorsPage'
import VerticalsPage from '../../pages/VerticalsPage'
import TrendsPage from '../../pages/TrendsPage'
import GraphPage from '../../pages/GraphPage'
import SettingsPage from '../../pages/SettingsPage'
import AdminPage from '../../pages/AdminPage'
import TabBar from './TabBar'
import StatusBar from './StatusBar'
import { useAuth } from '../auth/AuthProvider'
import { useEffect } from 'react'

export default function Shell() {
  const { activeTab, setActiveTab } = useUIStore()
  const { user, logout } = useAuth()
  const canManage = user?.role === 'admin' || user?.role === 'superadmin'
  const isSuperadmin = user?.role === 'superadmin'

  useEffect(() => {
    if (activeTab === 'settings' && !canManage) {
      setActiveTab('news')
    }
    if (activeTab === 'admin' && !isSuperadmin) {
      setActiveTab('news')
    }
  }, [activeTab, canManage, isSuperadmin, setActiveTab])

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-stone-800 bg-stone-950 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/calico-cat.svg" alt="calicoAI" className="w-10 h-10" />
            <div>
              <h1 className="text-lg font-bold text-orange-400 leading-tight">calicoAI</h1>
              <p className="text-xs text-stone-500 leading-tight">Multi-topic news monitor</p>
            </div>
          </div>
          <TabBar />
          <div className="flex items-center gap-4">
            <StatusBar />
            <div className="text-right">
              <p className="text-sm text-stone-200">{user?.full_name}</p>
              <p className="text-[11px] uppercase tracking-wide text-stone-500">{user?.role}</p>
            </div>
            <button
              onClick={() => void logout()}
              className="rounded-lg border border-stone-700 px-3 py-2 text-xs text-stone-300 transition hover:border-stone-500"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        {activeTab === 'news' && <NewsPage />}
        {activeTab === 'vendors' && <VendorsPage />}
        {activeTab === 'verticals' && <VerticalsPage />}
        {activeTab === 'trends' && <TrendsPage />}
        {activeTab === 'graph' && <GraphPage />}
        {activeTab === 'settings' && canManage && <SettingsPage />}
        {activeTab === 'admin' && isSuperadmin && <AdminPage />}
      </main>
    </div>
  )
}
