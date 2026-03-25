/**
 * Polling hook — D-083: global 30s + manual refresh.
 * Tab hidden → polling pauses (Page Visibility API).
 * Last successful data preserved on error.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const DEFAULT_INTERVAL = 30_000

export interface UsePollingResult<T> {
  data: T | null
  error: Error | null
  loading: boolean
  refresh: () => void
  lastFetchedAt: Date | null
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = DEFAULT_INTERVAL,
): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(null)

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const doFetch = useCallback(async () => {
    try {
      const result = await fetcherRef.current()
      setData(result)
      setError(null)
      setLastFetchedAt(new Date())
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
      // data preserved — last successful kept
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(() => {
    setLoading(true)
    void doFetch()
  }, [doFetch])

  // Start polling
  useEffect(() => {
    // Initial fetch
    void doFetch()

    const start = () => {
      if (timerRef.current) clearInterval(timerRef.current)
      timerRef.current = setInterval(() => void doFetch(), intervalMs)
    }

    const stop = () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }

    const handleVisibility = () => {
      if (document.hidden) {
        stop()
      } else {
        void doFetch()
        start()
      }
    }

    start()
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      stop()
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [doFetch, intervalMs])

  return { data, error, loading, refresh, lastFetchedAt }
}
