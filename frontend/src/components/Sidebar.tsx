/**
 * Sidebar navigation — active route highlighted.
 */
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/missions', label: 'Missions', icon: '🎯' },
  { to: '/health', label: 'Health', icon: '💚' },
  { to: '/approvals', label: 'Approvals', icon: '🔐' },
  { to: '/telemetry', label: 'Telemetry', icon: '📊' },
]

export function Sidebar() {
  return (
    <nav className="flex w-56 flex-col border-r border-gray-800 bg-gray-900 px-3 py-4">
      <div className="mb-6 px-2">
        <h2 className="text-sm font-bold text-gray-100">OpenClaw</h2>
        <p className="text-[10px] text-gray-500">Mission Control</p>
      </div>
      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-gray-700/80 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`
              }
            >
              <span>{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
