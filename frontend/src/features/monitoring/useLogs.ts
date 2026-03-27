/**
 * useLogs — fetch structured logs from API with filters.
 * Task 16.11: Real API hook.
 */
import { useState, useCallback } from 'react'

const BASE = '/api/v1'

export interface LogEntry {
  ts: string
  level: string
  event: string
  trace_id: string
  span_id: string
  mission_id: string
  correlation_id: string
  stage?: string
  tool?: string
  [key: string]: unknown
}

export interface LogFilters {
  missionId?: string
  level?: string
  event?: string
  stage?: string
  search?: string
  limit?: number
  offset?: number
}

export function useLogs() {
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchLogs = useCallback(async (filters: LogFilters = {}) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filters.missionId) params.set('mission_id', filters.missionId)
      if (filters.level) params.set('level', filters.level)
      if (filters.event) params.set('event', filters.event)
      if (filters.stage) params.set('stage', filters.stage)
      if (filters.search) params.set('search', filters.search)
      if (filters.limit) params.set('limit', String(filters.limit))
      if (filters.offset) params.set('offset', String(filters.offset))

      const qs = params.toString()
      const res = await fetch(`${BASE}/telemetry/logs${qs ? '?' + qs : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setLogs(data.logs ?? [])
      setTotal(data.total ?? 0)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  return { logs, total, loading, error, fetchLogs }
}
