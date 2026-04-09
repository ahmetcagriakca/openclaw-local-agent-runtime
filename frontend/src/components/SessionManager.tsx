/**
 * SessionManager — Auth session management UI.
 * S84: Shows current auth status, user info, role, and logout.
 */
import { useAuth } from '../auth/AuthContext'

export function SessionManager() {
  const { isAuthenticated, user, authMode, logout } = useAuth()

  if (!isAuthenticated || !user) {
    return (
      <div className="rounded border border-gray-700 bg-gray-800/50 p-4">
        <p className="text-sm text-gray-400">Not authenticated</p>
      </div>
    )
  }

  const roleBadgeColor = {
    admin: 'bg-purple-800 text-purple-200',
    operator: 'bg-blue-800 text-blue-200',
    viewer: 'bg-gray-700 text-gray-300',
  }[user.role] ?? 'bg-gray-700 text-gray-300'

  return (
    <div className="rounded border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-200">Session</h3>
        <span className="rounded-full bg-green-800 text-green-200 px-2 py-0.5 text-xs font-medium">
          Active
        </span>
      </div>

      <div className="space-y-1 text-xs text-gray-400">
        <div className="flex justify-between">
          <span>User</span>
          <span className="text-gray-200">{user.display_name || user.username}</span>
        </div>
        {user.email && (
          <div className="flex justify-between">
            <span>Email</span>
            <span className="text-gray-200">{user.email}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span>Role</span>
          <span className={`rounded-full px-1.5 py-0.5 ${roleBadgeColor}`}>
            {user.role}
          </span>
        </div>
        <div className="flex justify-between">
          <span>Auth</span>
          <span className="text-gray-200">
            {authMode === 'oauth' ? `SSO (${user.provider})` : 'API Key'}
          </span>
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
