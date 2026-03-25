/**
 * Layout — sidebar + header + content area.
 * Polling status indicator in header.
 */
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-950 text-gray-100">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-gray-800 bg-gray-900/80 px-6 py-3">
          <h1 className="text-sm font-semibold">OpenClaw Mission Control</h1>
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <span className="inline-block h-2 w-2 rounded-full bg-green-500" title="Polling active" />
            <span>Polling 30s</span>
          </div>
        </header>
        {/* Content */}
        <main className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </main>
      </div>
    </div>
  )
}
