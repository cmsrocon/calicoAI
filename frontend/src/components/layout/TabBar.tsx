import { BarChart2, Building2, Layers, Settings, Shield, Share2, TrendingUp } from 'lucide-react'
import { useUIStore } from '../../store/uiStore'
import { useAuth } from '../auth/AuthProvider'

const tabs = [
  { id: 'news' as const, label: 'Daily News', icon: BarChart2 },
  { id: 'vendors' as const, label: 'Entities', icon: Building2 },
  { id: 'verticals' as const, label: 'Themes', icon: Layers },
  { id: 'trends' as const, label: 'Trends', icon: TrendingUp },
  { id: 'graph' as const, label: 'Graph', icon: Share2 },
  { id: 'settings' as const, label: 'Settings', icon: Settings },
  { id: 'admin' as const, label: 'Admin', icon: Shield },
]

export default function TabBar() {
  const { activeTab, setActiveTab } = useUIStore()
  const { user } = useAuth()
  const visibleTabs = tabs.filter((tab) => {
    if (tab.id === 'settings') return user?.role === 'admin' || user?.role === 'superadmin'
    if (tab.id === 'admin') return user?.role === 'superadmin'
    return true
  })
  return (
    <nav className="flex gap-1">
      {visibleTabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => setActiveTab(id)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === id
              ? 'bg-orange-500 text-white'
              : 'text-stone-400 hover:text-stone-200 hover:bg-stone-800'
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </nav>
  )
}
