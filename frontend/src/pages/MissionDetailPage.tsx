/**
 * MissionDetailPage — single mission detail with stage timeline + SSE + mutation.
 * 404 → explicit "Mission not found". Deny forensics visible.
 * Sprint 11: cancel/retry buttons added (D-090, D-091).
 */
import { useCallback, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getMission, cancelMission, retryMission } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useMutation } from '../hooks/useMutation'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { MissionStateBadge } from '../components/MissionStateBadge'
import { StageTimeline } from '../components/StageTimeline'
import { StageCard } from '../components/StageCard'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { ApiError } from '../api/client'

export function MissionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [selectedStage, setSelectedStage] = useState<number | null>(null)
  const [showCancelConfirm, setShowCancelConfirm] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'timeout'; message: string } | null>(null)

  const fetcher = useCallback(() => {
    if (!id) return Promise.reject(new Error('No mission ID'))
    return getMission(id)
  }, [id])

  const { data, error, loading, refresh, lastFetchedAt } = usePolling(fetcher)

  // SSE: refresh on mission_updated + mutation events
  useSSEInvalidation(['mission_updated', 'mutation_applied', 'mutation_rejected'], refresh)

  const cancelMut = useMutation({
    mutationFn: () => cancelMission(id!),
    onSuccess: () => {
      setToast({ type: 'success', message: 'Cancel request sent — awaiting controller' })
      refresh()
    },
    onError: (reason) => setToast({ type: 'error', message: reason }),
    onTimeout: () => setToast({ type: 'timeout', message: 'Cancel timed out — try manual refresh' }),
  })

  const retryMut = useMutation({
    mutationFn: () => retryMission(id!),
    onSuccess: () => {
      setToast({ type: 'success', message: 'Retry request sent — awaiting controller' })
      refresh()
    },
    onError: (reason) => setToast({ type: 'error', message: reason }),
    onTimeout: () => setToast({ type: 'timeout', message: 'Retry timed out — try manual refresh' }),
  })

  const CANCEL_STATES = new Set(['pending', 'planning', 'executing', 'gate_check', 'rework', 'approval_wait'])
  const RETRY_STATES = new Set(['failed', 'aborted', 'timed_out'])

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
              <div className="flex items-center gap-2">
                {CANCEL_STATES.has(mission.state) && (
                  <button
                    onClick={() => setShowCancelConfirm(true)}
                    disabled={cancelMut.status === 'loading'}
                    className="flex items-center gap-1.5 rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
                  >
                    {cancelMut.status === 'loading' && (
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    )}
                    Cancel
                  </button>
                )}
                {RETRY_STATES.has(mission.state) && (
                  <button
                    onClick={() => retryMut.mutate()}
                    disabled={retryMut.status === 'loading'}
                    className="flex items-center gap-1.5 rounded bg-blue-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
                  >
                    {retryMut.status === 'loading' && (
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    )}
                    Retry
                  </button>
                )}
                <button
                  onClick={refresh}
                  className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600"
                >
                  Refresh
                </button>
              </div>
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

      {/* D-090: Cancel confirmation dialog */}
      <ConfirmDialog
        open={showCancelConfirm}
        title="Cancel Mission"
        message={`Are you sure you want to cancel mission ${id}? This action is irreversible.`}
        confirmLabel="Cancel Mission"
        variant="danger"
        loading={cancelMut.status === 'loading'}
        onConfirm={() => {
          setShowCancelConfirm(false)
          cancelMut.mutate()
        }}
        onCancel={() => setShowCancelConfirm(false)}
      />

      {/* Toast notification */}
      {toast && (
        <div
          className={`fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
            toast.type === 'success'
              ? 'border border-green-600/50 bg-green-950/90 text-green-300'
              : toast.type === 'timeout'
                ? 'border border-yellow-600/50 bg-yellow-950/90 text-yellow-300'
                : 'border border-red-600/50 bg-red-950/90 text-red-300'
          }`}
        >
          <span>{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 text-xs opacity-70 hover:opacity-100">✕</button>
        </div>
      )}
    </div>
  )
}
