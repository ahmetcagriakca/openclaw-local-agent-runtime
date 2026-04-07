/**
 * SSE Context — provides SSE connection state + event bus to the app.
 * Single SSE connection per tab, shared via React context.
 */
/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useRef, type ReactNode } from 'react'
import { useSSE, type SSEStatus } from '../hooks/useSSE'

interface SSEContextValue {
  status: SSEStatus
  lastEventAt: Date | null
  subscribe: (eventType: string, handler: () => void) => () => void
}

const SSEContext = createContext<SSEContextValue>({
  status: 'connecting',
  lastEventAt: null,
  subscribe: () => () => {},
})

export function useSSEContext(): SSEContextValue {
  return useContext(SSEContext)
}

/**
 * Hook to trigger a callback when a specific SSE event type is received.
 * Used in pages to call refresh() on relevant events.
 */
export function useSSEInvalidation(eventType: string | string[], callback: () => void) {
  const { subscribe } = useSSEContext()
  const callbackRef = useRef(callback)

  useEffect(() => {
    callbackRef.current = callback
  })

  useEffect(() => {
    const types = Array.isArray(eventType) ? eventType : [eventType]
    const unsubs = types.map((t) =>
      subscribe(t, () => callbackRef.current()),
    )
    return () => unsubs.forEach((u) => u())
  }, [eventType, subscribe])
}

export function SSEProvider({ children }: { children: ReactNode }) {
  const listenersRef = useRef<Map<string, Set<() => void>>>(new Map())

  const handleEvent = useCallback((type: string, _data: Record<string, unknown>) => {
    const handlers = listenersRef.current.get(type)
    if (handlers) {
      handlers.forEach((h) => h())
    }

    // polling_tick triggers all handlers (fallback mode)
    if (type === 'polling_tick') {
      listenersRef.current.forEach((handlers) => {
        handlers.forEach((h) => h())
      })
    }
  }, [])

  const { status, lastEventAt } = useSSE({ onEvent: handleEvent })

  const subscribe = useCallback((eventType: string, handler: () => void) => {
    if (!listenersRef.current.has(eventType)) {
      listenersRef.current.set(eventType, new Set())
    }
    listenersRef.current.get(eventType)!.add(handler)
    return () => {
      const set = listenersRef.current.get(eventType)
      if (set) {
        set.delete(handler)
        if (set.size === 0) listenersRef.current.delete(eventType)
      }
    }
  }, [])

  return (
    <SSEContext.Provider value={{ status, lastEventAt, subscribe }}>
      {children}
    </SSEContext.Provider>
  )
}
