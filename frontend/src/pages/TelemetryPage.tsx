/**
 * TelemetryPage — policy telemetry events with type coloring and filtering.
 */
import { useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getTelemetry } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'

const EVENT_COLORS: Record<string, string> = {
  feedback_loop_rework: 'bg-orange-800 text-orange-200',
  feedback_loop_escalated: 'bg-red-800 text-red-200',
  stage_failed: 'bg-red-800 text-red-200',
  mission_failed: 'bg-red-900 text-red-100',
  mission_completed: 'bg-green-800 text-green-200',
  policy_deny: 'bg-amber-800 text-amber-200',
  recovery_triage_decision: 'bg-yellow-800 text-yellow-200',
  tool_call: 'bg-blue-800 text-blue-200',
  stage_started: 'bg-blue-800 text-blue-200',
  stage_completed: 'bg-green-800 text-green-200',
}

export function TelemetryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filterMissionId = searchParams.get('mission_id') ?? ''
  const [inputValue, setInputValue] = useState(filterMissionId)
  const [typeFilter, setTypeFilter] = useState<string>('all')

  const fetcher = useCallback(
    () => getTelemetry(filterMissionId || undefined),
    [filterMissionId],
  )

  const { data, error, loading, refresh } = usePolling(fetcher, 15_000)

  useSSEInvalidation('telemetry_new', refresh)

  const handleFilter = () => {
    if (inputValue) {
      setSearchParams({ mission_id: inputValue })
    } else {
      setSearchParams({})
    }
  }

  const allEvents = data?.events
    ? [...data.events].sort((a, b) => {
        if (!a.timestamp || !b.timestamp) return 0
        return b.timestamp.localeCompare(a.timestamp)
      })
    : []

  // Unique event types for filter
  const eventTypes = [...new Set(allEvents.map((e) => e.type))].sort()

  const events = typeFilter === 'all'
    ? allEvents
    : allEvents.filter((e) => e.type === typeFilter)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Telemetry</h1>
        <span className="text-sm text-gray-500">
          {allEvents.length} events{typeFilter !== 'all' ? `, ${events.length} shown` : ''}
        </span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleFilter()}
          placeholder="Filter by mission ID…"
          className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none sm:w-auto"
        />
        <button
          onClick={handleFilter}
          aria-label="Apply mission ID filter"
          className="rounded bg-blue-700 px-3 py-1.5 text-sm hover:bg-blue-600"
        >
          Filter
        </button>
        {filterMissionId && (
          <button
            onClick={() => { setInputValue(''); setSearchParams({}) }}
            className="text-sm text-gray-400 hover:text-gray-200"
          >
            Clear
          </button>
        )}
      </div>

      {/* Type filter chips */}
      {eventTypes.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setTypeFilter('all')}
            className={`rounded px-2 py-0.5 text-xs ${
              typeFilter === 'all' ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            All
          </button>
          {eventTypes.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t === typeFilter ? 'all' : t)}
              className={`rounded px-2 py-0.5 text-xs ${
                typeFilter === t ? 'bg-blue-700 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center gap-2 py-8 text-gray-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
          Loading telemetry…
        </div>
      )}

      {error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load telemetry</p>
          <p className="mt-1 text-sm">{error.message}</p>
        </div>
      )}

      {data && events.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No telemetry events{filterMissionId ? ` for mission ${filterMissionId}` : ''}
          {typeFilter !== 'all' ? ` of type "${typeFilter}"` : ''}
        </div>
      )}

      {events.length > 0 && (
        <div className="space-y-1.5">
          {events.slice(0, 100).map((ev, i) => {
            const colorCls = EVENT_COLORS[ev.type] ?? 'bg-indigo-800 text-indigo-200'
            return (
              <div
                key={`${ev.timestamp}-${ev.type}-${i}`}
                className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`rounded px-2 py-0.5 text-xs font-medium ${colorCls}`}>
                      {ev.type}
                    </span>
                    {ev.missionId && (
                      <span className="font-mono text-xs text-gray-400">
                        {ev.missionId}
                      </span>
                    )}
                  </div>
                  {ev.timestamp && (
                    <span className="text-xs text-gray-500">
                      {new Date(ev.timestamp).toLocaleString()}
                    </span>
                  )}
                </div>
                {Object.keys(ev.data).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-400">
                    {Object.entries(ev.data).map(([k, v]) => {
                      const display = typeof v === 'object' && v !== null
                        ? JSON.stringify(v).slice(0, 80) + (JSON.stringify(v).length > 80 ? '...' : '')
                        : String(v)
                      return (
                        <span key={k} title={typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}>
                          {k}: <span className="text-gray-200">{display}</span>
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
          {events.length > 100 && (
            <p className="text-center text-xs text-gray-500">
              Showing 100 of {events.length} events
            </p>
          )}
        </div>
      )}
    </div>
  )
}
