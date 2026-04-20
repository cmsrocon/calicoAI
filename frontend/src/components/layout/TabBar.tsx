import { BarChart2, Building2, Layers, Settings, TrendingUp } from 'lucide-react'
import { useUIStore } from '../../store/uiStore'

const tabs = [
  { id: 'news' as const, label: 'Daily News', icon: BarChart2 },
  { id: 'vendors' as const, label: 'Vendors', icon: Building2 },
  { id: 'verticals' as const, label: 'Sectors', icon: Layers },
  { id: 'trends' as const, label: 'Trends', icon: TrendingUp },
  { id: 'settings' as const, label: 'Settings', icon: Settings },
]

export default function TabBar() {
  const { activeTab, setActiveTab } = useUIStore()
  return (
    <nav className="flex gap-1">
      {tabs.map(({ id, label, icon: Icon }) => (
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
