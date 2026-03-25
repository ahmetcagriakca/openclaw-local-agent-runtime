/**
 * MissionListPage — lists all missions with polling.
 * Empty/loading/error states explicit. Silent absence forbidden.
 */
import { Link } from 'react-router-dom'
import { getMissions } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { MissionStateBadge } from '../components/MissionStateBadge'

export function MissionListPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getMissions)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Missions</h1>
        <button
          onClick={refresh}
          className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600"
        >
          Refresh
        </button>
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
          Loading missions…
        </div>
      )}

      {error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load missions</p>
          <p className="mt-1 text-sm">{error.message}</p>
          <button
            onClick={refresh}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {data && data.missions.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No missions found
        </div>
      )}

      {data && data.missions.length > 0 && (
        <div className="space-y-2">
          {data.missions.map((m) => (
            <Link
              key={m.missionId}
              to={`/missions/${m.missionId}`}
              className="block rounded-lg border border-gray-700/50 bg-gray-800/50 p-4 transition hover:border-gray-600 hover:bg-gray-800"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-gray-300">
                    {m.missionId.length > 16
                      ? `${m.missionId.slice(0, 16)}…`
                      : m.missionId}
                  </span>
                  <MissionStateBadge state={m.state} />
                  <DataQualityBadge quality={m.dataQuality} />
                </div>
                <div className="text-xs text-gray-500">
                  {m.stageCount > 0 && (
                    <span>Stage {m.currentStage}/{m.stageCount}</span>
                  )}
                </div>
              </div>
              {m.goal && (
                <p className="mt-1 text-sm text-gray-400 line-clamp-1">
                  {m.goal}
                </p>
              )}
              <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                {m.startedAt && <span>Started: {m.startedAt}</span>}
                {m.stageSummary && <span>{m.stageSummary}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
