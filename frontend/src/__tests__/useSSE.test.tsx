/**
 * useSSE hook tests — connection lifecycle, reconnect, fallback.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSSE } from '../hooks/useSSE'

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  listeners: Record<string, ((e: Partial<MessageEvent>) => void)[]> = {}
  onerror: (() => void) | null = null
  readyState = 0
  closed = false

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  addEventListener(type: string, handler: (e: Partial<MessageEvent>) => void) {
    if (!this.listeners[type]) this.listeners[type] = []
    this.listeners[type].push(handler)
  }

  close() {
    this.closed = true
  }

  // Test helper: simulate event
  _emit(type: string, data: string, lastEventId?: string) {
    const event = { data, lastEventId }
    if (this.listeners[type]) {
      this.listeners[type].forEach((h) => h(event))
    }
  }

  // Test helper: simulate error
  _error() {
    if (this.onerror) this.onerror()
  }
}

describe('useSSE', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    vi.stubGlobal('EventSource', MockEventSource)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('starts with connecting status', () => {
    const onEvent = vi.fn()
    const { result } = renderHook(() => useSSE({ onEvent }))
    expect(result.current.status).toBe('connecting')
  })

  it('transitions to connected on connected event', () => {
    const onEvent = vi.fn()
    const { result } = renderHook(() => useSSE({ onEvent }))

    const es = MockEventSource.instances[0]!
    act(() => {
      es._emit('connected', '{"serverTime":"2026-01-01T00:00:00Z","version":"1.0.0"}')
    })

    expect(result.current.status).toBe('connected')
    expect(result.current.lastEventAt).toBeInstanceOf(Date)
    expect(onEvent).toHaveBeenCalledWith('connected', expect.objectContaining({ version: '1.0.0' }))
  })

  it('updates lastEventAt on heartbeat', () => {
    const onEvent = vi.fn()
    const { result } = renderHook(() => useSSE({ onEvent }))

    const es = MockEventSource.instances[0]!
    act(() => {
      es._emit('connected', '{}')
    })

    act(() => {
      es._emit('heartbeat', '{"serverTime":"2026-01-01T00:01:00Z"}')
    })

    expect(result.current.lastEventAt).toBeInstanceOf(Date)
    expect(onEvent).toHaveBeenCalledWith('heartbeat', expect.any(Object))
  })

  it('calls onEvent for domain events', () => {
    const onEvent = vi.fn()
    renderHook(() => useSSE({ onEvent }))

    const es = MockEventSource.instances[0]!
    act(() => {
      es._emit('mission_updated', '{"missionId":"m1","updatedAt":"2026-01-01"}')
    })

    expect(onEvent).toHaveBeenCalledWith('mission_updated', expect.objectContaining({ missionId: 'm1' }))
  })

  it('cleans up EventSource on unmount', () => {
    const onEvent = vi.fn()
    const { unmount } = renderHook(() => useSSE({ onEvent }))

    const es = MockEventSource.instances[0]!
    unmount()
    expect(es.closed).toBe(true)
  })
})
