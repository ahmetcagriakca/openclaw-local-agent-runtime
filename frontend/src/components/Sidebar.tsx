/**
 * Sidebar navigation.
 * Desktop: collapsed = icon-only (narrow), expanded = icon + label (wide).
 * Toggle button at bottom of sidebar.
 * Mobile: horizontal dropdown.
 */
import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/missions', label: 'Missions', icon: '🎯' },
  { to: '/health', label: 'Health', icon: '💚' },
  { to: '/approvals', label: 'Approvals', icon: '🔐' },
  { to: '/telemetry', label: 'Telemetry', icon: '📊' },
  { to: '/monitoring', label: 'Monitoring', icon: '📈' },
  { to: '/templates', label: 'Templates', icon: '📋' },
  { to: '/costs', label: 'Costs', icon: '💰' },
  { to: '/agents', label: 'Agents', icon: '🤖' },
]

interface SidebarProps {
  onNavigate?: () => void
  onToggle?: () => void
  horizontal?: boolean
  collapsed?: boolean
}

export function Sidebar({ onNavigate, onToggle, horizontal, collapsed }: SidebarProps) {
  // ── Mobile horizontal dropdown ──
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

  // ── Desktop sidebar ──
  return (
    <nav
      aria-label="Main navigation"
      className={`flex h-full flex-col border-r border-gray-800 bg-gray-900 transition-all duration-200 ${
        collapsed ? 'w-14' : 'w-52'
      }`}
    >
      {/* Logo */}
      <div className={`shrink-0 border-b border-gray-800/50 px-3 py-4 ${collapsed ? 'text-center' : ''}`}>
        {collapsed ? (
          <span className="text-lg" title="Vezir — Multi-Agent Platform">⚙</span>
        ) : (
          <div className="px-1">
            <h2 className="text-sm font-bold text-gray-100">Vezir</h2>
            <p className="text-[10px] text-gray-500">Multi-Agent Platform</p>
          </div>
        )}
      </div>

      {/* Nav items */}
      <ul role="list" className={`flex-1 space-y-1 px-2 py-3 ${collapsed ? 'px-1.5' : ''}`}>
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                collapsed
                  ? `flex h-9 w-full items-center justify-center rounded-lg text-base transition ${
                      isActive
                        ? 'bg-gray-700/80 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                    }`
                  : `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition ${
                      isActive
                        ? 'bg-gray-700/80 text-white'
                        : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                    }`
              }
            >
              <span aria-hidden="true" className={collapsed ? '' : 'text-base'}>{item.icon}</span>
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      {/* Toggle button at bottom */}
      <div className="shrink-0 border-t border-gray-800/50 px-2 py-2">
        <button
          onClick={onToggle}
          title={collapsed ? 'Expand menu' : 'Collapse menu'}
          className="flex w-full items-center justify-center rounded-lg py-1.5 text-gray-500 transition hover:bg-gray-800 hover:text-gray-300"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {collapsed
              ? <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              : <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />}
          </svg>
        </button>
      </div>
    </nav>
  )
}
