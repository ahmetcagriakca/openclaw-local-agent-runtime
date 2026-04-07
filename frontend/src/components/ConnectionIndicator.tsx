/**
 * ConnectionIndicator — shows SSE connection status.
 * D-060: no fake live behavior. "Live" only when truly connected.
 */
import { useCallback, useEffect, useRef } from 'react'
import { useSSEContext } from '../hooks/SSEContext'
import type { SSEStatus } from '../hooks/useSSE'

const STATUS_CONFIG: Record<SSEStatus, { color: string; pulse: boolean; label: string }> = {
  connecting: { color: 'bg-yellow-500', pulse: true, label: 'Connecting…' },
  connected: { color: 'bg-green-500', pulse: false, label: 'Live' },
  reconnecting: { color: 'bg-orange-500', pulse: true, label: 'Reconnecting…' },
  disconnected: { color: 'bg-red-500', pulse: false, label: 'Disconnected' },
}

export function ConnectionIndicator() {
  const { status, lastEventAt } = useSSEContext()
  const config = STATUS_CONFIG[status]
  const tooltipRef = useRef<HTMLDivElement>(null)

  const updateTooltip = useCallback(() => {
    if (!tooltipRef.current) return
    if (!lastEventAt) {
      tooltipRef.current.title = 'No events yet'
    } else {
      const secsAgo = Math.round((Date.now() - lastEventAt.getTime()) / 1000)
      tooltipRef.current.title = `Last event: ${secsAgo}s ago`
    }
  }, [lastEventAt])

  useEffect(() => {
    updateTooltip()
    const id = setInterval(updateTooltip, 5_000)
    return () => clearInterval(id)
  }, [updateTooltip])

  return (
    <div ref={tooltipRef} className="flex items-center gap-2 text-xs text-gray-400" role="status" aria-live="polite">
      <span
        aria-hidden="true"
        className={`inline-block h-2 w-2 rounded-full ${config.color} ${
          config.pulse ? 'animate-pulse' : ''
        }`}
      />
      <span>{config.label}</span>
    </div>
  )
}
