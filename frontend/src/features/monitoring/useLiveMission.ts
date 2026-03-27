/**
 * useLiveMission — SSE hook for real-time mission updates.
 * Task 16.13: Live waterfall updates via SSE.
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const BASE = '/api/v1'

export interface LiveEvent {
  type: string
  data: Record<string, unknown>
  ts: string
}

export function useLiveMission() {
  const [events, setEvents] = useState<LiveEvent[]>([])
  const [connected, setConnected] = useState(false)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
    }

    const source = new EventSource(`${BASE}/dashboard/live`)
    sourceRef.current = source

    source.addEventListener('connected', () => {
      setConnected(true)
    })

    const eventTypes = [
      'stage.start', 'stage.complete',
      'tool_call.response', 'tool_call.blocked',
      'budget.approval_required', 'budget.warning',
      'mission.complete', 'mission.failed',
      'mission_updated', 'mission_list_changed',
    ]

    for (const type of eventTypes) {
      source.addEventListener(type, (e: MessageEvent) => {
        try {
          const data = JSON.parse(e.data)
          setEvents(prev => [...prev.slice(-200), {
            type,
            data,
            ts: new Date().toISOString(),
          }])
        } catch {
          // Ignore parse errors
        }
      })
    }

    source.addEventListener('heartbeat', () => {
      // Keep-alive, no action needed
    })

    source.onerror = () => {
      setConnected(false)
      // Auto-reconnect is handled by EventSource
    }
  }, [])

  const disconnect = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close()
      sourceRef.current = null
    }
    setConnected(false)
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  useEffect(() => {
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close()
      }
    }
  }, [])

  return { events, connected, connect, disconnect, clearEvents }
}
