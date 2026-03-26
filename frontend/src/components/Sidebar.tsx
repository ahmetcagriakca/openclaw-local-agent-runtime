/**
 * Sidebar navigation — supports full, collapsed (icon-only), and horizontal modes.
 */
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/missions', label: 'Missions', icon: '🎯' },
  { to: '/health', label: 'Health', icon: '💚' },
  { to: '/approvals', label: 'Approvals', icon: '🔐' },
  { to: '/telemetry', label: 'Telemetry', icon: '📊' },
]

interface SidebarProps {
  onNavigate?: () => void
  horizontal?: boolean
  collapsed?: boolean
}

export function Sidebar({ onNavigate, horizontal, collapsed }: SidebarProps) {
  // Horizontal mode (mobile dropdown)
  if (horizontal) {
    return (
      <nav aria-label="Main navigation" className="px-4 py-3">
        <ul role="list" className="flex flex-wrap gap-2">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition ${
                    isActive
                      ? 'bg-gray-700 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`
                }
              >
                <span aria-hidden="true">{item.icon}</span>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    )
  }

  // Collapsed mode (icon-only)
  if (collapsed) {
    return (
      <nav aria-label="Main navigation" className="flex w-14 flex-col items-center border-r border-gray-800 bg-gray-900 py-4">
        <div className="mb-6">
          <span className="text-lg">⚙</span>
        </div>
        <ul role="list" className="space-y-2">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                title={item.label}
                className={({ isActive }) =>
                  `flex h-9 w-9 items-center justify-center rounded-lg text-base transition ${
                    isActive
                      ? 'bg-gray-700/80 text-white'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                  }`
                }
              >
                <span>{item.icon}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    )
  }

  // Full mode (desktop default)
  return (
    <nav aria-label="Main navigation" className="flex w-56 flex-col border-r border-gray-800 bg-gray-900 px-3 py-4">
      <div className="mb-6 px-2">
        <h2 className="text-sm font-bold text-gray-100">OpenClaw</h2>
        <p className="text-[10px] text-gray-500">Mission Control</p>
      </div>
      <ul role="list" className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-gray-700/80 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`
              }
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
