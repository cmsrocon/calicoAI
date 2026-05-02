import { AuthProvider, useAuth } from './components/auth/AuthProvider'
import Shell from './components/layout/Shell'
import LoginPage from './pages/LoginPage'

function AppContent() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="min-h-screen grid place-items-center bg-stone-950 text-stone-400">Loading session...</div>
  }

  if (!user) {
    return <LoginPage />
  }

  return <Shell />
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
