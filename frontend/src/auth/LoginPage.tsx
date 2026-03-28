/**
 * LoginPage — simple API key login form.
 * D-117: token-based auth for MVP.
 */
import { useState, type FormEvent } from 'react'
import { useAuth } from './AuthContext'

export function LoginPage() {
  const { login } = useAuth()
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e: FormEvent) => {
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

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-900">
      <div className="w-full max-w-sm rounded-lg border border-gray-700 bg-gray-800 p-8">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-100">Vezir Platform</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
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
            Login
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-gray-500">
          Contact your administrator for an API key.
        </p>
      </div>
    </div>
  )
}
