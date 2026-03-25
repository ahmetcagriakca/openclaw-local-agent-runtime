/**
 * TelemetryPage — telemetry events, filterable by mission_id + SSE invalidation.
 * Newest-first. Empty state explicit.
 */
import { useCallback, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getTelemetry } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { FreshnessIndicator } from '../components/FreshnessIndicator'

export function TelemetryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filterMissionId = searchParams.get('mission_id') ?? ''
  const [inputValue, setInputValue] = useState(filterMissionId)

  const fetcher = useCallback(
    () => getTelemetry(filterMissionId || undefined),
    [filterMissionId],
  )

  const { data, error, loading, refresh, lastFetchedAt } = usePolling(fetcher)

  // SSE: refresh on new telemetry
  useSSEInvalidation('telemetry_new', refresh)

  const handleFilter = () => {
    if (inputValue) {
      setSearchParams({ mission_id: inputValue })
    } else {
      setSearchParams({})
    }
  }

  const events = data?.events
    ? [...data.events].sort((a, b) => {
        if (!a.timestamp || !b.timestamp) return 0
        return b.timestamp.localeCompare(a.timestamp)
      })
    : []

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Telemetry</h1>
        <button
          onClick={refresh}
          className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600"
        >
          Refresh
        </button>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleFilter()}
          placeholder="Filter by mission ID…"
          className="rounded border border-gray-600 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={handleFilter}
          className="rounded bg-blue-700 px-3 py-1.5 text-sm hover:bg-blue-600"
        >
          Filter
        </button>
        {filterMissionId && (
          <button
            onClick={() => {
              setInputValue('')
              setSearchParams({})
            }}
            className="text-sm text-gray-400 hover:text-gray-200"
          >
            Clear
          </button>
        )}
      </div>

      {data && (
        <FreshnessIndicator
          freshnessMs={data.meta.freshnessMs}
          sourcesUsed={data.meta.sourcesUsed}
          sourcesMissing={data.meta.sourcesMissing}
          lastFetchedAt={lastFetchedAt}
        />
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
          <button
            onClick={refresh}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {data && events.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No telemetry events{filterMissionId ? ` for mission ${filterMissionId}` : ''}
        </div>
      )}

      {events.length > 0 && (
        <div className="space-y-2">
          {events.map((ev, i) => (
            <div
              key={`${ev.timestamp}-${ev.type}-${i}`}
              className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="rounded bg-indigo-800 px-2 py-0.5 text-xs font-medium text-indigo-200">
                    {ev.type}
                  </span>
                  {ev.missionId && (
                    <span className="text-xs text-gray-400">
                      Mission: {ev.missionId}
                    </span>
                  )}
                </div>
                {ev.timestamp && (
                  <span className="text-xs text-gray-500">{ev.timestamp}</span>
                )}
              </div>
              {ev.sourceFile && (
                <p className="mt-1 text-xs text-gray-500">Source: {ev.sourceFile}</p>
              )}
              {Object.keys(ev.data).length > 0 && (
                <pre className="mt-2 overflow-x-auto rounded bg-gray-900/50 p-2 text-xs text-gray-300">
                  {JSON.stringify(ev.data, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
