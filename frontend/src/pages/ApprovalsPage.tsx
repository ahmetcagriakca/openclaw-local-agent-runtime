/**
 * ApprovalsPage — read-only approval list.
 * Empty state explicit: "No pending approvals".
 */
import { getApprovals } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { DataQualityBadge } from '../components/DataQualityBadge'

const STATUS_COLOR: Record<string, string> = {
  approved: 'text-green-400',
  denied: 'text-red-400',
  pending: 'text-yellow-400',
  expired: 'text-gray-400',
}

export function ApprovalsPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getApprovals)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Approvals</h1>
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

      {data && data.approvals.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          No pending approvals
        </div>
      )}

      {data && data.approvals.length > 0 && (
        <div className="space-y-2">
          {data.approvals.map((a) => (
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
                {a.risk && (
                  <span className="text-xs text-gray-400">Risk: {a.risk}</span>
                )}
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
      )}
    </div>
  )
}
