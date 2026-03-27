/**
 * useTraces — fetch OTel trace data from API.
 * Task 16.11: Real API hook replacing mock data.
 */
import { useState, useEffect, useCallback } from 'react'

const BASE = '/api/v1'

export interface TraceSpan {
  name: string
  span_id?: string
  parent_span_id?: string
  start_time?: string
  end_time?: string
  status?: string
  attributes?: Record<string, unknown>
}

export interface TraceData {
  mission_id: string
  span_count: number
  spans: TraceSpan[]
  recorded_at: string
}

export function useTraces(missionId?: string) {
  const [trace, setTrace] = useState<TraceData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchTrace = useCallback(async (id: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${BASE}/telemetry/traces/${encodeURIComponent(id)}`)
      if (!res.ok) {
        setError(`Trace not found: ${res.status}`)
        return
      }
      const data = await res.json()
      setTrace(data.trace ?? null)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (missionId) fetchTrace(missionId)
  }, [missionId, fetchTrace])

  return { trace, loading, error, refetch: fetchTrace }
}
