/**
 * useMissions — fetch dashboard mission data from API with filters.
 * Task 16.11: Real API hook for dashboard missions endpoint.
 */
import { useState, useCallback } from 'react'

const BASE = '/api/v1'

export interface DashboardMission {
  id: string
  goal: string
  complexity: string
  status: string
  tokens: number
  duration: number
  stages: number
  tools: number
  reworks: number
  ts: string
  operator: string
  budget_pct: number
  anomaly_count: number
  budget_events: number
}

export interface MissionFilters {
  status?: string
  complexity?: string
  search?: string
  sort?: string
  limit?: number
  offset?: number
}

export interface DashboardSummary {
  total_missions: number
  completed: number
  failed: number
  aborted: number
  running: number
  total_tokens: number
  avg_duration: number
  avg_tokens: number
  total_tool_calls: number
  total_blocked: number
  total_budget_events: number
  total_anomalies: number
  bypass_detections: number
  audit_integrity: string
}

export function useMissions() {
  const [missions, setMissions] = useState<DashboardMission[]>([])
  const [total, setTotal] = useState(0)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchMissions = useCallback(async (filters: MissionFilters = {}) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (filters.status) params.set('status', filters.status)
      if (filters.complexity) params.set('complexity', filters.complexity)
      if (filters.search) params.set('search', filters.search)
      if (filters.sort) params.set('sort', filters.sort)
      if (filters.limit) params.set('limit', String(filters.limit))
      if (filters.offset) params.set('offset', String(filters.offset))

      const qs = params.toString()
      const res = await fetch(`${BASE}/dashboard/missions${qs ? '?' + qs : ''}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setMissions(data.missions ?? [])
      setTotal(data.total ?? 0)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}/dashboard/summary`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setSummary(data)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  return { missions, total, summary, loading, error, fetchMissions, fetchSummary }
}
