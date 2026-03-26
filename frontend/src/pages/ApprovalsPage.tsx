/**
 * ApprovalsPage — approval list + mutation buttons (Sprint 11).
 * D-090: reject requires confirmation dialog.
 * D-091: server-confirmed, no optimistic UI.
 * D-092: approval sunset Phase 1 — dashboard approve/reject is primary channel.
 */
import { useState, useCallback } from 'react'
import { getApprovals, approveApproval, rejectApproval } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useMutation } from '../hooks/useMutation'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { ConfirmDialog } from '../components/ConfirmDialog'

const STATUS_COLOR: Record<string, string> = {
  approved: 'text-green-400',
  denied: 'text-red-400',
  pending: 'text-yellow-400',
  expired: 'text-gray-400',
}

export function ApprovalsPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getApprovals)

  // SSE: refresh on approval changes + mutation events
  useSSEInvalidation(['approval_changed', 'mutation_applied', 'mutation_rejected'], refresh)

  // Track which approval is being mutated
  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null)
  const [activeAction, setActiveAction] = useState<'approve' | 'reject' | null>(null)
  const [confirmRejectId, setConfirmRejectId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'timeout'; message: string } | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const clearToast = useCallback(() => setToast(null), [])

  const approveMutation = useMutation({
    mutationFn: () => approveApproval(activeApprovalId!),
    onSuccess: () => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'success', message: 'Approval approved successfully' })
      refresh()
    },
    onError: (reason) => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'error', message: reason })
    },
    onTimeout: () => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'timeout', message: 'Operation timed out — try manual refresh' })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectApproval(activeApprovalId!),
    onSuccess: () => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'success', message: 'Approval rejected' })
      refresh()
    },
    onError: (reason) => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'error', message: reason })
    },
    onTimeout: () => {
      setActiveApprovalId(null)
      setActiveAction(null)
      setToast({ type: 'timeout', message: 'Operation timed out — try manual refresh' })
    },
  })

  const handleApprove = (id: string) => {
    setActiveApprovalId(id)
    setActiveAction('approve')
    approveMutation.reset()
    // Delay to let state update, then mutate
    setTimeout(() => approveMutation.mutate(), 0)
  }

  const handleRejectClick = (id: string) => {
    // D-090: destructive — show confirmation dialog
    setConfirmRejectId(id)
  }

  const handleRejectConfirm = () => {
    if (confirmRejectId) {
      setActiveApprovalId(confirmRejectId)
      setActiveAction('reject')
      setConfirmRejectId(null)
      rejectMutation.reset()
      setTimeout(() => rejectMutation.mutate(), 0)
    }
  }

  const isBusy = (id: string) =>
    activeApprovalId === id && (activeAction === 'approve' || activeAction === 'reject')

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Approvals</h1>
        <button
          onClick={refresh}
          title="Refresh"
          className="rounded bg-gray-700 p-1.5 text-gray-400 hover:bg-gray-600 hover:text-white"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h5M20 20v-5h-5M4.5 15.5A8.5 8.5 0 0118 6.07M19.5 8.5A8.5 8.5 0 016 17.93" />
          </svg>
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
          Loading approvals…
        </div>
      )}

      {error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load approvals</p>
          <p className="mt-1 text-sm">{error.message}</p>
          <button
            onClick={refresh}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {/* Status filter */}
      {data && data.approvals.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Filter:</span>
          {['all', 'pending', 'approved', 'denied'].map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                statusFilter === f
                  ? f === 'pending' ? 'bg-yellow-700 text-white'
                    : f === 'approved' ? 'bg-green-700 text-white'
                    : f === 'denied' ? 'bg-red-700 text-white'
                    : 'bg-blue-700 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {f === 'all' ? `All (${data.approvals.length})` : f}
            </button>
          ))}
        </div>
      )}

      {data && data.approvals.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No approvals
        </div>
      )}

      {data && data.approvals.length > 0 && (() => {
        const filtered = statusFilter === 'all'
          ? data.approvals
          : data.approvals.filter((a) => a.status === statusFilter)
        return filtered.length === 0 ? (
          <div className="py-6 text-center text-gray-500">No approvals matching "{statusFilter}"</div>
        ) : (
        <div className="space-y-2">
          {filtered.map((a) => (
            <div
              key={a.id}
              className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm">{a.id}</span>
                  <span className={`text-sm font-medium ${STATUS_COLOR[a.status] ?? 'text-gray-400'}`}>
                    {a.status}
                  </span>
                  <DataQualityBadge quality={data.meta.dataQuality} />
                </div>
                <div className="flex items-center gap-2">
                  {a.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleApprove(a.id)}
                        disabled={isBusy(a.id)}
                        className="flex items-center gap-1.5 rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-600 disabled:opacity-50"
                      >
                        {isBusy(a.id) && activeAction === 'approve' && (
                          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        )}
                        Approve
                      </button>
                      <button
                        onClick={() => handleRejectClick(a.id)}
                        disabled={isBusy(a.id)}
                        className="flex items-center gap-1.5 rounded bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
                      >
                        {isBusy(a.id) && activeAction === 'reject' && (
                          <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        )}
                        Reject
                      </button>
                    </>
                  )}
                  {a.risk && (
                    <span className="text-xs text-gray-400">Risk: {a.risk}</span>
                  )}
                </div>
              </div>
              <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-400">
                {a.missionId && <span>Mission: {a.missionId}</span>}
                {a.toolName && <span>Tool: {a.toolName}</span>}
                {a.requestedAt && <span>Requested: {a.requestedAt}</span>}
                {a.respondedAt && <span>Responded: {a.respondedAt}</span>}
              </div>
            </div>
          ))}
        </div>
        )
      })()}

      {/* D-090: Reject confirmation dialog */}
      <ConfirmDialog
        open={confirmRejectId !== null}
        title="Reject Approval"
        message={`Are you sure you want to reject approval ${confirmRejectId}? This action is irreversible.`}
        confirmLabel="Reject"
        variant="danger"
        loading={rejectMutation.status === 'loading'}
        onConfirm={handleRejectConfirm}
        onCancel={() => setConfirmRejectId(null)}
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
          <button onClick={clearToast} className="ml-2 text-xs opacity-70 hover:opacity-100">✕</button>
        </div>
      )}
    </div>
  )
}
