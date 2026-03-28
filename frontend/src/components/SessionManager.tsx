/**
 * SessionManager — Auth session management UI.
 * Shows current auth status, key info, expiration, and logout.
 */
import { useAuth } from '../auth/AuthContext'

function formatExpiry(expiresAt: string | null): string {
  if (!expiresAt) return 'Never'
  try {
    const exp = new Date(expiresAt)
    const now = new Date()
    const diffMs = exp.getTime() - now.getTime()
    if (diffMs < 0) return 'Expired'
    const days = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (days > 0) return `${days}d remaining`
    const hours = Math.floor(diffMs / (1000 * 60 * 60))
    return `${hours}h remaining`
  } catch {
    return 'Unknown'
  }
}

interface SessionManagerProps {
  expiresAt?: string | null
}

export function SessionManager({ expiresAt = null }: SessionManagerProps) {
  const { isAuthenticated, userName, logout } = useAuth()

  if (!isAuthenticated) {
    return (
      <div className="rounded border border-gray-700 bg-gray-800/50 p-4">
        <p className="text-sm text-gray-400">Not authenticated</p>
      </div>
    )
  }

  const expiryText = formatExpiry(expiresAt)
  const isExpired = expiryText === 'Expired'

  return (
    <div className="rounded border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">Session</h3>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          isExpired ? 'bg-red-800 text-red-200' : 'bg-green-800 text-green-200'
        }`}>
          {isExpired ? 'Expired' : 'Active'}
        </span>
      </div>

      <div className="space-y-1 text-xs text-gray-400">
        <div className="flex justify-between">
          <span>User</span>
          <span className="text-gray-200">{userName ?? 'Unknown'}</span>
        </div>
        <div className="flex justify-between">
          <span>Expiration</span>
          <span className={isExpired ? 'text-red-400' : 'text-gray-200'}>{expiryText}</span>
        </div>
      </div>

      <button
        onClick={logout}
        className="w-full rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
      >
        Logout
      </button>
    </div>
  )
}
