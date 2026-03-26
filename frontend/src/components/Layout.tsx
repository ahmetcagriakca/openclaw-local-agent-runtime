/**
 * Layout — sidebar + header + content area.
 * Desktop: sidebar toggles between full (text+icon) and collapsed (icon-only).
 * Mobile: dropdown nav from header hamburger.
 */
import { useState } from 'react'
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { ConnectionIndicator } from './ConnectionIndicator'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950 text-gray-100">
      {/* Desktop sidebar — always rendered, width changes */}
      <div className="hidden h-full shrink-0 lg:flex">
        <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile dropdown nav */}
      {mobileOpen && (
        <div className="fixed inset-x-0 top-[49px] z-40 border-b border-gray-700 bg-gray-900 shadow-xl lg:hidden">
          <Sidebar onNavigate={() => setMobileOpen(false)} horizontal />
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex shrink-0 items-center justify-between border-b border-gray-800 bg-gray-900/80 px-4 py-3 lg:px-6">
          <div className="flex items-center gap-2">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-white lg:hidden"
              aria-label="Toggle menu"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                {mobileOpen
                  ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />}
              </svg>
            </button>
            <h1 className="text-sm font-semibold">OpenClaw Mission Control</h1>
          </div>
          <ConnectionIndicator />
        </header>
        {/* Content */}
        <main className="flex-1 overflow-y-auto px-4 py-4 lg:px-6">
          {children}
        </main>
      </div>
    </div>
  )
}
