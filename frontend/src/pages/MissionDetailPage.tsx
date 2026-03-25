/**
 * MissionDetailPage — single mission detail with stage timeline + SSE.
 * 404 → explicit "Mission not found". Deny forensics visible.
 */
import { useCallback, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getMission } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { MissionStateBadge } from '../components/MissionStateBadge'
import { StageTimeline } from '../components/StageTimeline'
import { StageCard } from '../components/StageCard'
import { ApiError } from '../api/client'

export function MissionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedStage, setSelectedStage] = useState<number | null>(null)

  const fetcher = useCallback(() => {
    if (!id) return Promise.reject(new Error('No mission ID'))
    return getMission(id)
  }, [id])

  const { data, error, loading, refresh, lastFetchedAt } = usePolling(fetcher)

  // SSE: refresh on mission_updated (all — filtering by missionId happens server-side or is acceptable)
  useSSEInvalidation('mission_updated', refresh)

  const is404 = error instanceof ApiError && error.status === 404

  if (is404) {
    return (
      <div className="space-y-4">
        <Link to="/missions" className="text-sm text-blue-400 hover:underline">
          ← Back to missions
        </Link>
        <div className="py-8 text-center">
          <p className="text-xl text-gray-400">Mission not found</p>
          <p className="mt-1 text-sm text-gray-500">ID: {id}</p>
        </div>
      </div>
    )
  }

  const mission = data?.mission
  const activeStage = mission?.stages.find((s) => s.index === selectedStage)

  return (
    <div className="space-y-4">
      <Link to="/missions" className="text-sm text-blue-400 hover:underline">
        ← Back to missions
      </Link>

      {loading && !data && (
        <div className="flex items-center gap-2 py-8 text-gray-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
          Loading mission…
        </div>
      )}

      {error && !is404 && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load mission</p>
          <p className="mt-1 text-sm">{error.message}</p>
          <button
            onClick={refresh}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {data && mission && (
        <>
          {/* Header */}
          <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h1 className="font-mono text-lg font-bold">{mission.missionId}</h1>
                <MissionStateBadge state={mission.state} />
                <DataQualityBadge quality={data.meta.dataQuality} />
              </div>
              <button
                onClick={refresh}
                className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600"
              >
                Refresh
              </button>
            </div>
            {mission.goal && (
              <p className="mt-2 text-sm text-gray-300">{mission.goal}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-400">
              {mission.complexity && (
                <span>Complexity: <span className="text-gray-200">{mission.complexity}</span></span>
              )}
              {mission.startedAt && <span>Started: {mission.startedAt}</span>}
              {mission.completedAt && <span>Completed: {mission.completedAt}</span>}
              {mission.totalDurationMs != null && (
                <span>Duration: <span className="text-gray-200">{(mission.totalDurationMs / 1000).toFixed(1)}s</span></span>
              )}
              <span>Artifacts: <span className="text-gray-200">{mission.artifactCount}</span></span>
              <span>Policy denies: <span className="text-gray-200">{mission.totalPolicyDenies}</span></span>
            </div>
          </div>

          {/* Freshness */}
          <FreshnessIndicator
            freshnessMs={data.meta.freshnessMs}
            sourcesUsed={data.meta.sourcesUsed}
            sourcesMissing={data.meta.sourcesMissing}
            lastFetchedAt={lastFetchedAt}
          />

          {/* Stage Timeline */}
          <div>
            <h2 className="mb-2 text-sm font-semibold text-gray-300">Stage Pipeline</h2>
            <StageTimeline
              stages={mission.stages}
              activeIndex={selectedStage}
              onSelect={setSelectedStage}
            />
          </div>

          {/* Expanded Stage Card */}
          {activeStage && <StageCard stage={activeStage} />}

          {/* Mission-level Deny Forensics */}
          {mission.denyForensics.length > 0 && (
            <div className="rounded border border-amber-700/50 bg-amber-950/30 p-4">
              <h3 className="mb-2 text-sm font-semibold text-amber-300">
                Mission Deny Forensics ({mission.denyForensics.length})
              </h3>
              <div className="space-y-2">
                {mission.denyForensics.map((df, i) => (
                  <pre key={i} className="overflow-x-auto rounded bg-gray-900/50 p-2 text-xs text-amber-200/70">
                    {JSON.stringify(df, null, 2)}
                  </pre>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
