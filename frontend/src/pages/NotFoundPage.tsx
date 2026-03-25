/**
 * NotFoundPage — 404 for unknown routes.
 */
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
      <p className="text-6xl font-bold">404</p>
      <p className="mt-2 text-lg">Page not found</p>
      <Link
        to="/missions"
        className="mt-4 rounded bg-blue-700 px-4 py-2 text-sm text-white hover:bg-blue-600"
      >
        Go to Missions
      </Link>
    </div>
  )
}
