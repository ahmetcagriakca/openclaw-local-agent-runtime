/**
 * ProtectedRoute — S84 route guard.
 *
 * Wraps routes that require authentication.
 * Redirects to login page if not authenticated.
 */
import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthContext'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: string
}

const ROLE_LEVELS: Record<string, number> = {
  admin: 3,
  operator: 2,
  viewer: 1,
}

export function ProtectedRoute({ children, requiredRole }: ProtectedRouteProps) {
  const { isAuthenticated, user } = useAuth()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRole && user) {
    const userLevel = ROLE_LEVELS[user.role] ?? 0
    const requiredLevel = ROLE_LEVELS[requiredRole] ?? 0
    if (userLevel < requiredLevel) {
      return (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="text-center">
            <h2 className="text-xl font-semibold text-red-400">Access Denied</h2>
            <p className="mt-2 text-gray-400">
              You need {requiredRole} role to access this page.
              Current role: {user.role}
            </p>
          </div>
        </div>
      )
    }
  }

  return <>{children}</>
}
