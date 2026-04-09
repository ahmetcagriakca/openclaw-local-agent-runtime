/**
 * LoginPage — API key + OAuth login.
 * D-117: token-based auth for MVP.
 * S84: OAuth login support.
 */
import { useState, useEffect, type FormEvent } from 'react'
import { useAuth } from './AuthContext'

interface AuthConfig {
  sso_enabled: boolean
  provider: string | null
  login_url: string | null
}

export function LoginPage() {
  const { login, loginWithOAuth } = useAuth()
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')
  const [authConfig, setAuthConfig] = useState<AuthConfig | null>(null)
  const [loading, setLoading] = useState(false)

  // Check if SSO is configured
  useEffect(() => {
    fetch('/api/v1/auth/config')
      .then(r => r.json())
      .then(setAuthConfig)
      .catch(() => setAuthConfig({ sso_enabled: false, provider: null, login_url: null }))
  }, [])

  // Handle OAuth callback (code in URL params)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const state = params.get('state')

    if (code && state) {
      setLoading(true)
      fetch('/api/v1/auth/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, state }),
      })
        .then(r => {
          if (!r.ok) throw new Error('OAuth callback failed')
          return r.json()
        })
        .then(data => {
          loginWithOAuth(data.access_token, data.refresh_token, data.user)
          // Clean URL
          window.history.replaceState({}, '', '/auth/callback')
        })
        .catch(e => {
          setError(e.message || 'OAuth login failed')
          window.history.replaceState({}, '', '/auth/callback')
        })
        .finally(() => setLoading(false))
    }
  }, [loginWithOAuth])

  const handleApiKeySubmit = (e: FormEvent) => {
    e.preventDefault()
    const key = apiKey.trim()
    if (!key) {
      setError('API key is required')
      return
    }
    if (!key.startsWith('vz_')) {
      setError('Invalid key format. Keys start with vz_')
      return
    }
    setError('')
    login(key)
  }

  const handleOAuthLogin = async () => {
    setLoading(true)
    setError('')
    try {
      const resp = await fetch('/api/v1/auth/login')
      if (!resp.ok) throw new Error('Failed to initiate login')
      const data = await resp.json()
      window.location.href = data.redirect_url
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed')
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-gray-400 border-t-blue-500 mx-auto" />
          <p className="text-gray-400">Authenticating...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-900">
      <div className="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-800 p-8">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-100">Vezir Platform</h1>

        {/* OAuth login button */}
        {authConfig?.sso_enabled && (
          <>
            <button
              onClick={handleOAuthLogin}
              className="mb-4 w-full rounded bg-gray-700 py-2.5 text-sm font-medium text-white hover:bg-gray-600 flex items-center justify-center gap-2"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
              Sign in with {authConfig.provider === 'github' ? 'GitHub' : 'SSO'}
            </button>
            <div className="relative mb-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-600" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-gray-800 px-2 text-gray-500">or</span>
              </div>
            </div>
          </>
        )}

        {/* API key login form */}
        <form onSubmit={handleApiKeySubmit} className="space-y-4">
          <div>
            <label htmlFor="api-key" className="block text-sm font-medium text-gray-300">
              API Key
            </label>
            <input
              id="api-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="vz_..."
              className="mt-1 w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
            />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            Login with API Key
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-gray-500">
          Contact your administrator for access.
        </p>
      </div>
    </div>
  )
}
