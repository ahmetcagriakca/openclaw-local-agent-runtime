/**
 * AuthContext — D-117 frontend auth state.
 *
 * Provides API key auth context to React components.
 * Stores key in localStorage for persistence.
 */
import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface AuthState {
  apiKey: string | null
  userName: string | null
  isAuthenticated: boolean
}

interface AuthContextType extends AuthState {
  login: (apiKey: string, userName?: string) => void
  logout: () => void
  getAuthHeaders: () => Record<string, string>
}

const AuthContext = createContext<AuthContextType | null>(null)

const STORAGE_KEY = 'vezir_auth'

function loadAuth(): AuthState {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      const { apiKey, userName } = JSON.parse(stored)
      return { apiKey, userName, isAuthenticated: !!apiKey }
    }
  } catch {}
  return { apiKey: null, userName: null, isAuthenticated: false }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadAuth)

  const login = useCallback((apiKey: string, userName?: string) => {
    const state = { apiKey, userName: userName ?? null, isAuthenticated: true }
    setAuth(state)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ apiKey, userName: state.userName }))
  }, [])

  const logout = useCallback(() => {
    setAuth({ apiKey: null, userName: null, isAuthenticated: false })
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  const getAuthHeaders = useCallback(() => {
    if (!auth.apiKey) return {}
    return { Authorization: `Bearer ${auth.apiKey}` }
  }, [auth.apiKey])

  return (
    <AuthContext.Provider value={{ ...auth, login, logout, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
