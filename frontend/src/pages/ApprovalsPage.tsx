/**
 * ApprovalsPage — Full approval inbox UI (B-102, Sprint 39).
 * D-090: reject requires confirmation dialog.
 * D-091: server-confirmed, no optimistic UI.
 * D-092: dashboard approve/reject is primary channel.
 */
import { useState, useCallback, useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getApprovals, approveApproval, rejectApproval } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useMutation } from '../hooks/useMutation'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { ConfirmDialog } from '../components/ConfirmDialog'
import type { ApprovalEntry } from '../types/api'

const STATUS_COLOR: Record<string, string> = {
  approved: 'text-green-400',
  denied: 'text-red-400',
  pending: 'text-yellow-400',
  expired: 'text-gray-400',
}

const STATUS_BG: Record<string, string> = {
  approved: 'bg-green-900/30 border-green-700/50',
  denied: 'bg-red-900/30 border-red-700/50',
  pending: 'bg-yellow-900/20 border-yellow-700/50',
  expired: 'bg-gray-900/30 border-gray-700/50',
}

const RISK_COLOR: Record<string, string> = {
  critical: 'text-red-400 bg-red-900/30',
  high: 'text-orange-400 bg-orange-900/30',
  medium: 'text-yellow-400 bg-yellow-900/30',
  low: 'text-green-400 bg-green-900/30',
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    return d.toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'medium' })
  } catch {
    return iso
  }
}

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'just now'
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  } catch {
    return ''
  }
}

export function ApprovalsPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getApprovals)

  useSSEInvalidation(['approval_changed', 'mutation_applied', 'mutation_rejected'], refresh)

  const [activeApprovalId, setActiveApprovalId] = useState<string | null>(null)
  const [activeAction, setActiveAction] = useState<'approve' | 'reject' | null>(null)
  const [confirmRejectId, setConfirmRejectId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error' | 'timeout'; message: string } | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const statusFilter = searchParams.get('status') ?? 'all'
  const setStatusFilter = (v: string) => {
    if (v === 'all') { setSearchParams({}) }
    else { setSearchParams({ status: v }) }
  }

  const clearToast = useCallback(() => setToast(null), [])

  // Auto-dismiss toast after 5 seconds
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(clearToast, 5000)
    return () => clearTimeout(timer)
  }, [toast, clearToast])

  const counts = useMemo(() => {
    if (!data) return { all: 0, pending: 0, approved: 0, denied: 0, expired: 0 }
    const approvals = data.approvals
    return {
      all: approvals.length,
      pending: approvals.filter(a => a.status === 'pending').length,
      approved: approvals.filter(a => a.status === 'approved').length,
      denied: approvals.filter(a => a.status === 'denied').length,
      expired: approvals.filter(a => a.status === 'expired').length,
    }
  }, [data])

  const selectedApproval = useMemo(() => {
    if (!selectedId || !data) return null
    return data.approvals.find(a => a.id === selectedId) ?? null
  }, [selectedId, data])

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
    setTimeout(() => approveMutation.mutate(), 0)
  }

  const handleRejectClick = (id: string) => {
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

  const filtered = useMemo(() => {
    if (!data) return []
    return statusFilter === 'all'
      ? data.approvals
      : data.approvals.filter(a => a.status === statusFilter)
  }, [data, statusFilter])

  return (
    <div className="flex h-full gap-4">
      {/* Left: Approval list */}
      <div className="flex-1 space-y-4 min-w-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">Approvals</h1>
            {counts.pending > 0 && (
              <span className="rounded-full bg-yellow-600 px-2.5 py-0.5 text-xs font-bold text-white">
                {counts.pending} pending
              </span>
            )}
          </div>
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
            Loading approvals...
          </div>
        )}

        {error && (
          <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
            <p className="font-medium">Failed to load approvals</p>
            <p className="mt-1 text-sm">{error.message}</p>
            <button onClick={refresh} className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600">Retry</button>
          </div>
        )}

        {/* Status filter tabs */}
        {data && data.approvals.length > 0 && (
          <div className="flex items-center gap-1.5">
            {(['all', 'pending', 'approved', 'denied', 'expired'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setStatusFilter(f)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                  statusFilter === f
                    ? f === 'pending' ? 'bg-yellow-700 text-white'
                      : f === 'approved' ? 'bg-green-700 text-white'
                      : f === 'denied' ? 'bg-red-700 text-white'
                      : f === 'expired' ? 'bg-gray-600 text-white'
                      : 'bg-blue-700 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {f} ({counts[f]})
              </button>
            ))}
          </div>
        )}

        {data && data.approvals.length === 0 && (
          <div className="py-8 text-center text-gray-500">No approvals</div>
        )}

        {/* Approval list */}
        {filtered.length > 0 && (
          <div className="space-y-2">
            {filtered.map((a) => (
              <div
                key={a.id}
                onClick={() => setSelectedId(a.id === selectedId ? null : a.id)}
                className={`cursor-pointer rounded-lg border p-3 transition ${
                  STATUS_BG[a.status] ?? 'bg-gray-800/50 border-gray-700/50'
                } ${selectedId === a.id ? 'ring-2 ring-blue-500' : 'hover:border-gray-500'}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`text-xs font-bold uppercase ${STATUS_COLOR[a.status] ?? 'text-gray-400'}`}>
                      {a.status}
                    </span>
                    {a.risk && (
                      <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${RISK_COLOR[a.risk] ?? 'text-gray-400'}`}>
                        {a.risk}
                      </span>
                    )}
                    <span className="truncate text-sm text-gray-300">
                      {a.toolName ?? a.id}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-gray-500">{timeAgo(a.requestedAt)}</span>
                    {a.status === 'pending' && (
                      <>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleApprove(a.id) }}
                          disabled={isBusy(a.id)}
                          className="rounded bg-green-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-green-600 disabled:opacity-50"
                        >
                          {isBusy(a.id) && activeAction === 'approve'
                            ? <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            : 'Approve'}
                        </button>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleRejectClick(a.id) }}
                          disabled={isBusy(a.id)}
                          className="rounded bg-red-700 px-2.5 py-1 text-xs font-medium text-white hover:bg-red-600 disabled:opacity-50"
                        >
                          {isBusy(a.id) && activeAction === 'reject'
                            ? <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            : 'Reject'}
                        </button>
                      </>
                    )}
                  </div>
                </div>
                {a.reason && (
                  <p className="mt-1.5 text-xs text-gray-400 line-clamp-2">{a.reason}</p>
                )}
                <div className="mt-1.5 flex flex-wrap gap-3 text-xs text-gray-500">
                  {a.requestedByRole && <span>Role: {a.requestedByRole}</span>}
                  {a.missionId && <span>Mission: {a.missionId}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
        {data && filtered.length === 0 && data.approvals.length > 0 && (
          <div className="py-6 text-center text-gray-500">No approvals matching &quot;{statusFilter}&quot;</div>
        )}
      </div>

      {/* Right: Detail panel */}
      {selectedApproval && (
        <DetailPanel
          approval={selectedApproval}
          onClose={() => setSelectedId(null)}
          onApprove={handleApprove}
          onReject={handleRejectClick}
          isBusy={isBusy}
          activeAction={activeAction}
        />
      )}

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

      {/* Toast */}
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

function DetailPanel({
  approval,
  onClose,
  onApprove,
  onReject,
  isBusy,
  activeAction,
}: {
  approval: ApprovalEntry
  onClose: () => void
  onApprove: (id: string) => void
  onReject: (id: string) => void
  isBusy: (id: string) => boolean
  activeAction: 'approve' | 'reject' | null
}) {
  const a = approval
  return (
    <div className="w-full shrink-0 rounded-lg border border-gray-700/50 bg-gray-800/80 p-4 space-y-4 overflow-y-auto md:w-80">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-200">Approval Detail</h2>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">&times;</button>
      </div>

      <div className="space-y-3">
        <DetailRow label="ID" value={a.id} mono />
        <DetailRow label="Status">
          <span className={`font-bold uppercase ${STATUS_COLOR[a.status] ?? 'text-gray-400'}`}>{a.status}</span>
        </DetailRow>
        {a.risk && (
          <DetailRow label="Risk">
            <span className={`rounded px-2 py-0.5 text-xs font-medium ${RISK_COLOR[a.risk] ?? ''}`}>{a.risk}</span>
          </DetailRow>
        )}
        <DetailRow label="Tool" value={a.toolName} />
        <DetailRow label="Role" value={a.requestedByRole} />
        <DetailRow label="Mission" value={a.missionId} mono />
        <DetailRow label="Stage" value={a.stageId} />
        <DetailRow label="Requested" value={formatTime(a.requestedAt)} />
        <DetailRow label="Expires" value={formatTime(a.expiresAt)} />
        {a.respondedAt && <DetailRow label="Decided" value={formatTime(a.respondedAt)} />}
        {a.decidedBy && <DetailRow label="Decided by" value={a.decidedBy} />}
      </div>

      {a.reason && (
        <div>
          <p className="text-xs font-medium text-gray-400 mb-1">Reason</p>
          <p className="text-sm text-gray-300 bg-gray-900/50 rounded p-2">{a.reason}</p>
        </div>
      )}

      {a.status === 'pending' && (
        <div className="flex gap-2 pt-2 border-t border-gray-700/50">
          <button
            onClick={() => onApprove(a.id)}
            disabled={isBusy(a.id)}
            className="flex-1 rounded bg-green-700 py-2 text-sm font-medium text-white hover:bg-green-600 disabled:opacity-50"
          >
            {isBusy(a.id) && activeAction === 'approve' ? 'Approving...' : 'Approve'}
          </button>
          <button
            onClick={() => onReject(a.id)}
            disabled={isBusy(a.id)}
            className="flex-1 rounded bg-red-700 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
          >
            {isBusy(a.id) && activeAction === 'reject' ? 'Rejecting...' : 'Reject'}
          </button>
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, value, mono, children }: {
  label: string
  value?: string | null
  mono?: boolean
  children?: React.ReactNode
}) {
  if (!value && !children) return null
  return (
    <div>
      <p className="text-xs text-gray-500">{label}</p>
      {children ?? (
        <p className={`text-sm text-gray-300 ${mono ? 'font-mono' : ''}`}>{value}</p>
      )}
    </div>
  )
}
