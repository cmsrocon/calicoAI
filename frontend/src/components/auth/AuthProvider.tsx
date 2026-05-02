import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { fetchCurrentUser, login as loginRequest, logout as logoutRequest } from '../../api/auth'
import type { CurrentUser } from '../../types'

type AuthContextValue = {
  user: CurrentUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = async () => {
    try {
      const currentUser = await fetchCurrentUser()
      setUser(currentUser)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refreshUser()
  }, [])

  const value = useMemo<AuthContextValue>(() => ({
    user,
    loading,
    login: async (email: string, password: string) => {
      const currentUser = await loginRequest({ email, password })
      setUser(currentUser)
    },
    logout: async () => {
      await logoutRequest()
      setUser(null)
    },
    refreshUser,
  }), [loading, user])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
