/**
 * MissionDetailPage — single mission detail with stage timeline + SSE + mutation.
 * 404 → explicit "Mission not found". Deny forensics visible.
 * Sprint 11: cancel/retry buttons added (D-090, D-091).
 */
import { useCallback, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getMission, cancelMission, retryMission, deleteSignal } from '../api/client'
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

  const { data, error, loading, refresh, lastFetchedAt } = usePolling(fetcher, 10_000)

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
              {mission.startedAt && <span>Started: {new Date(mission.startedAt).toLocaleString()}</span>}
              {mission.completedAt && <span>Completed: {new Date(mission.completedAt).toLocaleString()}</span>}
              {mission.totalDurationMs != null && (
                <span>Duration: <span className="text-gray-200">{(mission.totalDurationMs / 1000).toFixed(1)}s</span></span>
              )}
              <span>Artifacts: <span className="text-gray-200">{mission.artifactCount}</span></span>
              <span>Policy denies: <span className="text-gray-200">{mission.totalPolicyDenies}</span></span>
            </div>
          </div>

          {/* Mission-level Error — prominent banner */}
          {mission.error && (
            <div className="rounded-lg border border-red-600/60 bg-red-950/40 p-4">
              <h3 className="mb-2 text-sm font-semibold text-red-400">Mission Error</h3>
              <pre className="whitespace-pre-wrap break-words text-sm text-red-200/90 leading-relaxed">
                {mission.error}
              </pre>
            </div>
          )}

          {/* Pending Signal Artifacts */}
          {mission.pendingSignals && mission.pendingSignals.length > 0 && (
            <div className="rounded-lg border border-yellow-600/50 bg-yellow-950/30 p-4">
              <h3 className="mb-2 text-sm font-semibold text-yellow-300">
                Pending Signals ({mission.pendingSignals.length})
              </h3>
              <div className="space-y-2">
                {mission.pendingSignals.map((sig) => (
                  <div
                    key={sig.requestId}
                    className="flex items-center justify-between rounded border border-yellow-700/40 bg-yellow-950/20 px-3 py-2"
                  >
                    <div className="flex items-center gap-3 text-xs">
                      <span className={`rounded px-2 py-0.5 font-medium uppercase ${
                        sig.type === 'retry' ? 'bg-blue-800 text-blue-200' :
                        sig.type === 'cancel' ? 'bg-red-800 text-red-200' :
                        sig.type === 'approve' ? 'bg-green-800 text-green-200' :
                        'bg-gray-700 text-gray-300'
                      }`}>{sig.type}</span>
                      <span className="font-mono text-gray-400">{sig.requestId.slice(0, 20)}…</span>
                      <span className="text-gray-500">
                        {sig.ageSeconds < 60 ? `${sig.ageSeconds}s ago` :
                         sig.ageSeconds < 3600 ? `${Math.floor(sig.ageSeconds / 60)}m ago` :
                         `${Math.floor(sig.ageSeconds / 3600)}h ago`}
                      </span>
                      {sig.ageSeconds > 60 && (
                        <span className="rounded bg-red-900 px-1.5 py-0.5 text-red-300">Expired</span>
                      )}
                    </div>
                    <button
                      onClick={async () => {
                        try {
                          await deleteSignal(sig.requestId)
                          setToast({ type: 'success', message: `Signal ${sig.type} deleted` })
                          refresh()
                        } catch {
                          setToast({ type: 'error', message: 'Failed to delete signal' })
                        }
                      }}
                      className="rounded bg-red-700 px-2 py-1 text-xs text-white hover:bg-red-600"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

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

          {/* State Transitions */}
          {mission.stateTransitions && mission.stateTransitions.length > 0 && (
            <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
              <h3 className="mb-2 text-sm font-semibold text-gray-300">State Transitions</h3>
              <div className="space-y-1">
                {mission.stateTransitions.map((t, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-20 shrink-0 text-gray-500">
                      {t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : ''}
                    </span>
                    <span className="rounded bg-gray-700 px-1.5 py-0.5 font-mono text-gray-300">{t.from}</span>
                    <span className="text-gray-500">→</span>
                    <span className={`rounded px-1.5 py-0.5 font-mono ${
                      t.to === 'failed' ? 'bg-red-900 text-red-300' :
                      t.to === 'completed' ? 'bg-green-900 text-green-300' :
                      'bg-gray-700 text-gray-300'
                    }`}>{t.to}</span>
                    {t.reason && (
                      <span className="text-gray-400 truncate">{t.reason}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

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
