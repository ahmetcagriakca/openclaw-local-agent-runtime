/**
 * usePolling hook tests — timer, visibility, refresh.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { usePolling } from '../hooks/usePolling'

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fetches immediately on mount', async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 42 })
    const { result } = renderHook(() => usePolling(fetcher, 30_000))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })

    expect(fetcher).toHaveBeenCalledTimes(1)
    expect(result.current.data).toEqual({ value: 42 })
    expect(result.current.error).toBeNull()
  })

  it('polls at interval', async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 })
    const { result } = renderHook(() => usePolling(fetcher, 5_000))

    // Initial fetch
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(fetcher).toHaveBeenCalledTimes(1)

    // After 5s interval
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(fetcher).toHaveBeenCalledTimes(2)

    // After another 5s
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(fetcher).toHaveBeenCalledTimes(3)
    expect(result.current.data).toEqual({ value: 1 })
  })

  it('preserves last data on error', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ value: 'ok' })
      .mockRejectedValueOnce(new Error('network'))

    const { result } = renderHook(() => usePolling(fetcher, 5_000))

    // Initial fetch succeeds
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(result.current.data).toEqual({ value: 'ok' })

    // Second fetch fails
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000)
    })
    expect(result.current.error?.message).toBe('network')
    expect(result.current.data).toEqual({ value: 'ok' }) // preserved
  })

  it('refresh triggers immediate fetch', async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 'fresh' })
    const { result } = renderHook(() => usePolling(fetcher, 30_000))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(fetcher).toHaveBeenCalledTimes(1)

    await act(async () => {
      result.current.refresh()
      await vi.advanceTimersByTimeAsync(10)
    })
    expect(fetcher).toHaveBeenCalledTimes(2)
  })
})
