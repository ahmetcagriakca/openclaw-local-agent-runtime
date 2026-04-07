/**
 * useSSE — SSE connection hook with reconnect + polling fallback.
 * D-088: exponential backoff (1s→30s max), 3 fails → polling fallback.
 * Page Visibility: tab hidden → close, tab visible → reconnect.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export type SSEStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

export interface UseSSEResult {
  status: SSEStatus
  lastEventAt: Date | null
}

interface UseSSEOptions {
  onEvent: (type: string, data: Record<string, unknown>) => void
  fallbackIntervalMs?: number
}

const SSE_URL = '/api/v1/events/stream'
const MAX_BACKOFF_MS = 30_000
const INITIAL_BACKOFF_MS = 1_000
const MAX_RECONNECT_FAILURES = 3

export function useSSE(options: UseSSEOptions): UseSSEResult {
  const { onEvent, fallbackIntervalMs = 30_000 } = options
  const [status, setStatus] = useState<SSEStatus>('connecting')
  const [lastEventAt, setLastEventAt] = useState<Date | null>(null)

  const onEventRef = useRef(onEvent)
  onEventRef.current = onEvent

  const eventSourceRef = useRef<EventSource | null>(null)
  const lastEventIdRef = useRef<string>('')
  const backoffRef = useRef(INITIAL_BACKOFF_MS)
  const failCountRef = useRef(0)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)

  const stopPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current)
      pollingTimerRef.current = null
    }
  }, [])

  const closeSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    closeSSE()

    // Build URL with Last-Event-ID as query param (header not settable on EventSource)
    let url = SSE_URL
    if (lastEventIdRef.current) {
      url += `?lastEventId=${lastEventIdRef.current}`
    }

    setStatus(failCountRef.current > 0 ? 'reconnecting' : 'connecting')

    const es = new EventSource(url)
    eventSourceRef.current = es

    es.addEventListener('connected', (e: MessageEvent) => {
      if (!mountedRef.current) return
      failCountRef.current = 0
      backoffRef.current = INITIAL_BACKOFF_MS
      stopPolling()
      setStatus('connected')
      setLastEventAt(new Date())
      try {
        const data = JSON.parse(e.data)
        onEventRef.current('connected', data)
      } catch { /* ignore parse errors */ }
    })

    es.addEventListener('heartbeat', (e: MessageEvent) => {
      if (!mountedRef.current) return
      setLastEventAt(new Date())
      try {
        const data = JSON.parse(e.data)
        onEventRef.current('heartbeat', data)
      } catch { /* ignore */ }
    })

    // Generic named events
    const eventTypes = [
      'mission_updated',
      'mission_list_changed',
      'health_changed',
      'telemetry_new',
      'capability_changed',
      'approval_changed',
    ]

    for (const type of eventTypes) {
      es.addEventListener(type, (e: MessageEvent) => {
        if (!mountedRef.current) return
        // Track event ID for reconnect replay
        const msgEvent = e as MessageEvent & { lastEventId?: string }
        if (msgEvent.lastEventId) {
          lastEventIdRef.current = msgEvent.lastEventId
        }
        setLastEventAt(new Date())
        try {
          const data = JSON.parse(e.data)
          onEventRef.current(type, data)
        } catch { /* ignore */ }
      })
    }

    es.onerror = () => {
      if (!mountedRef.current) return
      es.close()
      eventSourceRef.current = null

      failCountRef.current++

      if (failCountRef.current >= MAX_RECONNECT_FAILURES) {
        // Switch to polling fallback — show as disconnected since SSE failed
        setStatus('disconnected')
        if (!pollingTimerRef.current) {
          pollingTimerRef.current = setInterval(() => {
            onEventRef.current('polling_tick', {})
          }, fallbackIntervalMs)
        }
        // Keep trying to reconnect in background with max backoff
        reconnectTimerRef.current = setTimeout(() => {
          connect()
        }, MAX_BACKOFF_MS)
      } else {
        // Exponential backoff reconnect
        setStatus('reconnecting')
        const delay = Math.min(
          backoffRef.current * Math.pow(2, failCountRef.current - 1),
          MAX_BACKOFF_MS,
        )
        reconnectTimerRef.current = setTimeout(() => {
          connect()
        }, delay)
      }
    }
  }, [closeSSE, stopPolling, fallbackIntervalMs])

  // Page Visibility: tab hidden → close, visible → reconnect
  useEffect(() => {
    mountedRef.current = true
    connect()

    const handleVisibility = () => {
      if (document.hidden) {
        closeSSE()
        stopPolling()
      } else {
        failCountRef.current = 0
        backoffRef.current = INITIAL_BACKOFF_MS
        connect()
      }
    }

    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      mountedRef.current = false
      closeSSE()
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [connect, closeSSE, stopPolling])

  return { status, lastEventAt }
}
