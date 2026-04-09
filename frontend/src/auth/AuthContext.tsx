/**
 * AuthContext — D-117 + S84 SSO/RBAC upgrade.
 *
 * Supports both API key auth (D-117 legacy) and OAuth/JWT (S84 SSO).
 * Stores tokens in sessionStorage (cleared on tab close for security).
 *
 * CodeQL: sessionStorage is intentional — this is a localhost-only app and the
 * token must be sent with every request. sessionStorage is cleared on tab
 * close, which is the correct trade-off for a single-user local dashboard.
 * lgtm[js/clear-text-storage-of-sensitive-data]
 */
import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'

export interface UserInfo {
  user_id: string
  username: string
  email: string
  display_name: string
  role: string
  provider: string
  avatar_url?: string
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserInfo | null
  isAuthenticated: boolean
  authMode: 'none' | 'apikey' | 'oauth'
}

interface AuthContextType extends AuthState {
  login: (apiKey: string, userName?: string) => void
  loginWithOAuth: (accessToken: string, refreshToken: string, user: UserInfo) => void
  logout: () => void
  getAuthHeaders: () => Record<string, string>
  /** @deprecated Use accessToken for D-117 compat */
  apiKey: string | null
  userName: string | null
}

const AuthContext = createContext<AuthContextType | null>(null)

const STORAGE_KEY = 'vezir_auth'

function loadAuth(): AuthState {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      // S84: OAuth token format
      if (data.accessToken && data.user) {
        return {
          accessToken: data.accessToken,
          refreshToken: data.refreshToken ?? null,
          user: data.user,
          isAuthenticated: true,
          authMode: data.authMode ?? 'oauth',
        }
      }
      // D-117: Legacy API key format
      if (data.apiKey) {
        return {
          accessToken: data.apiKey,
          refreshToken: null,
          user: {
            user_id: data.userName ?? '',
            username: data.userName ?? '',
            email: '',
            display_name: data.userName ?? '',
            role: 'operator',
            provider: 'apikey',
          },
          isAuthenticated: true,
          authMode: 'apikey',
        }
      }
    }
  } catch { /* ignore corrupt storage */ }
  return { accessToken: null, refreshToken: null, user: null, isAuthenticated: false, authMode: 'none' }
}

function saveAuth(state: AuthState) {
  if (state.authMode === 'apikey') {
    // Legacy format for backward compatibility
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      apiKey: state.accessToken,
      userName: state.user?.username ?? null,
    }))
  } else if (state.authMode === 'oauth') {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      accessToken: state.accessToken,
      refreshToken: state.refreshToken,
      user: state.user,
      authMode: 'oauth',
    }))
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(loadAuth)

  // D-117 legacy API key login
  const login = useCallback((apiKey: string, userName?: string) => {
    const state: AuthState = {
      accessToken: apiKey,
      refreshToken: null,
      user: {
        user_id: userName ?? '',
        username: userName ?? '',
        email: '',
        display_name: userName ?? '',
        role: 'operator',
        provider: 'apikey',
      },
      isAuthenticated: true,
      authMode: 'apikey',
    }
    setAuth(state)
    saveAuth(state)
  }, [])

  // S84 OAuth login
  const loginWithOAuth = useCallback((accessToken: string, refreshToken: string, user: UserInfo) => {
    const state: AuthState = {
      accessToken,
      refreshToken,
      user,
      isAuthenticated: true,
      authMode: 'oauth',
    }
    setAuth(state)
    saveAuth(state)
  }, [])

  const logout = useCallback(async () => {
    // Revoke refresh token on server if OAuth
    if (auth.authMode === 'oauth' && auth.refreshToken) {
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: auth.refreshToken }),
        })
      } catch { /* best effort */ }
    }
    setAuth({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false, authMode: 'none' })
    sessionStorage.removeItem(STORAGE_KEY)
  }, [auth.authMode, auth.refreshToken])

  const getAuthHeaders = useCallback((): Record<string, string> => {
    if (!auth.accessToken) return {}
    return { Authorization: `Bearer ${auth.accessToken}` }
  }, [auth.accessToken])

  // Auto-refresh for OAuth tokens
  useEffect(() => {
    if (auth.authMode !== 'oauth' || !auth.refreshToken) return

    const refreshInterval = setInterval(async () => {
      try {
        const resp = await fetch('/api/v1/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: auth.refreshToken }),
        })
        if (resp.ok) {
          const data = await resp.json()
          const newState: AuthState = {
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
            user: data.user,
            isAuthenticated: true,
            authMode: 'oauth',
          }
          setAuth(newState)
          saveAuth(newState)
        } else {
          // Refresh failed — force logout
          setAuth({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false, authMode: 'none' })
          sessionStorage.removeItem(STORAGE_KEY)
        }
      } catch { /* network error — retry next interval */ }
    }, 50 * 60 * 1000) // Refresh 10 minutes before expiry (50 min)

    return () => clearInterval(refreshInterval)
  }, [auth.authMode, auth.refreshToken])

  return (
    <AuthContext.Provider value={{
      ...auth,
      login,
      loginWithOAuth,
      logout,
      getAuthHeaders,
      // D-117 backward compat
      apiKey: auth.accessToken,
      userName: auth.user?.username ?? null,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
