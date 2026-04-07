/**
 * ConnectionIndicator — shows SSE connection status.
 * D-060: no fake live behavior. "Live" only when truly connected.
 */
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

  const tooltip = lastEventAt
    ? `Last event: ${Math.round((Date.now() - lastEventAt.getTime()) / 1000)}s ago`
    : 'No events yet'

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400" title={tooltip} role="status" aria-live="polite">
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
