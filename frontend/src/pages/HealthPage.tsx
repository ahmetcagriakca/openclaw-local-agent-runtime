/**
 * HealthPage — comprehensive system health + capabilities + SSE.
 * Shows all components, agents, LLM providers, mission/approval stats.
 */
import { getHealth, getCapabilities, getRecentLogs } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { CapabilityStatus } from '../types/api'

const HEALTH_STATUS: Record<string, { color: string; label: string; dot: string }> = {
  ok: { color: 'bg-green-600 text-white', label: 'Healthy', dot: 'bg-green-500' },
  degraded: { color: 'bg-orange-500 text-white', label: 'Degraded', dot: 'bg-orange-500' },
  error: { color: 'bg-red-600 text-white', label: 'Error', dot: 'bg-red-500' },
  unknown: { color: 'bg-gray-500 text-white', label: 'Unknown', dot: 'bg-gray-500' },
}

const CAP_STATUS: Record<string, { color: string; icon: string }> = {
  [CapabilityStatus.Available]: { color: 'text-green-400', icon: 'ACTIVE' },
  [CapabilityStatus.Unavailable]: { color: 'text-red-400', icon: 'OFF' },
  [CapabilityStatus.Unknown]: { color: 'text-gray-400', icon: '?' },
}

export function HealthPage() {
  const health = usePolling(getHealth, 10_000)
  const caps = usePolling(getCapabilities, 30_000)
  const logs = usePolling(getRecentLogs, 15_000)

  useSSEInvalidation(['health_changed'], health.refresh)
  useSSEInvalidation(['capability_changed'], caps.refresh)

  return (
    <div className="space-y-6">
      {/* Header with overall status */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">System Health</h1>
        {health.data && (
          <div className="flex items-center gap-3">
            <span
              className={`rounded-lg px-4 py-2 text-lg font-bold ${
                HEALTH_STATUS[health.data.status]?.color ?? HEALTH_STATUS['unknown']!.color
              }`}
            >
              {HEALTH_STATUS[health.data.status]?.label ?? health.data.status}
            </span>
            <DataQualityBadge quality={health.data.meta.dataQuality} />
          </div>
        )}
      </div>

      {health.loading && !health.data && (
        <div className="flex items-center gap-2 py-8 text-gray-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
          Loading system health…
        </div>
      )}

      {health.error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load health</p>
          <p className="mt-1 text-sm">{health.error.message}</p>
        </div>
      )}

      {health.data && (() => {
        // Extract mission and approval stats from component details (JSON or key=val)
        const missionComp = health.data.components['missions']
        const approvalComp = health.data.components['approvals']

        const parseStat = (detail: string | null, key: string): number => {
          if (!detail) return 0
          // Try JSON parse first
          try {
            const obj = JSON.parse(detail)
            return typeof obj[key] === 'number' ? obj[key] : 0
          } catch {
            // Fallback: key=val regex
            const match = detail.match(new RegExp(`${key}=(\\d+)`))
            return match?.[1] ? parseInt(match[1], 10) : 0
          }
        }

        const mTotal = parseStat(missionComp?.detail ?? null, 'total')
        const mActive = parseStat(missionComp?.detail ?? null, 'active')
        const mCompleted = parseStat(missionComp?.detail ?? null, 'completed')
        const mFailed = parseStat(missionComp?.detail ?? null, 'failed')
        const mPending = parseStat(missionComp?.detail ?? null, 'pending')

        const aTotal = parseStat(approvalComp?.detail ?? null, 'total')
        const aPending = parseStat(approvalComp?.detail ?? null, 'pending')
        const aApproved = parseStat(approvalComp?.detail ?? null, 'approved')
        const aDenied = parseStat(approvalComp?.detail ?? null, 'denied')

        return <>
          {/* Mission & Approval Stats Bars */}
          {mTotal > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">Mission Statistics</h2>
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4 space-y-3">
                {/* Bar chart */}
                <div className="flex h-8 overflow-hidden rounded-lg">
                  {mCompleted > 0 && (
                    <div className="bg-green-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(mCompleted / mTotal) * 100}%` }}>
                      {mCompleted}
                    </div>
                  )}
                  {mActive > 0 && (
                    <div className="bg-blue-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(mActive / mTotal) * 100}%` }}>
                      {mActive}
                    </div>
                  )}
                  {mPending > 0 && (
                    <div className="bg-gray-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(mPending / mTotal) * 100}%` }}>
                      {mPending}
                    </div>
                  )}
                  {mFailed > 0 && (
                    <div className="bg-red-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(mFailed / mTotal) * 100}%` }}>
                      {mFailed}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-4 text-xs">
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-green-600" /> Completed: {mCompleted}</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-blue-600" /> Active: {mActive}</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-gray-600" /> Pending: {mPending}</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-red-600" /> Failed: {mFailed}</span>
                  <span className="text-gray-500">Total: {mTotal}</span>
                </div>
              </div>
            </section>
          )}

          {aTotal > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">Approval Statistics</h2>
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4 space-y-3">
                <div className="flex h-8 overflow-hidden rounded-lg">
                  {aApproved > 0 && (
                    <div className="bg-green-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(aApproved / aTotal) * 100}%` }}>
                      {aApproved}
                    </div>
                  )}
                  {aPending > 0 && (
                    <div className="bg-yellow-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(aPending / aTotal) * 100}%` }}>
                      {aPending}
                    </div>
                  )}
                  {aDenied > 0 && (
                    <div className="bg-red-600 flex items-center justify-center text-xs font-medium text-white"
                      style={{ width: `${(aDenied / aTotal) * 100}%` }}>
                      {aDenied}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-4 text-xs">
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-green-600" /> Approved: {aApproved}</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-yellow-600" /> Pending: {aPending}</span>
                  <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded bg-red-600" /> Denied: {aDenied}</span>
                  <span className="text-gray-500">Total: {aTotal}</span>
                </div>
              </div>
            </section>
          )}

          {/* Components Grid */}
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">Components</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(health.data.components).map(([key, comp]) => {
                const cfg = HEALTH_STATUS[comp.status] ?? HEALTH_STATUS['unknown']!
                return (
                  <div
                    key={key}
                    className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`inline-block h-2.5 w-2.5 rounded-full ${cfg.dot}`} />
                        <span className="text-sm font-medium text-gray-100">{comp.name || key}</span>
                      </div>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cfg.color}`}>
                        {cfg.label}
                      </span>
                    </div>
                    {comp.detail && (
                      <p className="mt-2 text-xs text-gray-400 leading-relaxed">{comp.detail}</p>
                    )}
                    {comp.lastCheckAt && (
                      <p className="mt-1 text-[10px] text-gray-600">
                        {new Date(comp.lastCheckAt).toLocaleTimeString()}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </section>
        </>
      })()}

      {/* Capabilities Section */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">Capabilities</h2>

        {caps.loading && !caps.data && (
          <div className="flex items-center gap-2 py-4 text-gray-400">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            Loading…
          </div>
        )}

        {caps.error && !caps.data && (
          <div className="rounded border border-red-500/50 bg-red-950/30 p-3 text-sm text-red-300">
            Failed to load capabilities: {caps.error.message}
          </div>
        )}

        {caps.data && (
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(caps.data.capabilities).map(([key, cap]) => {
              const s = CAP_STATUS[cap.status] ?? CAP_STATUS[CapabilityStatus.Unknown]!
              return (
                <div
                  key={key}
                  className="flex items-center justify-between rounded-lg border border-gray-700/50 bg-gray-800/50 px-4 py-2.5"
                >
                  <span className="text-sm text-gray-200">{cap.name || key}</span>
                  <span className={`rounded px-2 py-0.5 text-[10px] font-bold ${s.color} ${
                    cap.status === CapabilityStatus.Available ? 'bg-green-900/50' :
                    cap.status === CapabilityStatus.Unavailable ? 'bg-red-900/50' :
                    'bg-gray-800'
                  }`}>
                    {s.icon}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Recent Errors & Audit Log */}
      {logs.data && (
        <>
          {logs.data.errors.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
                Recent Errors ({logs.data.totalErrors})
              </h2>
              <div className="space-y-1.5">
                {logs.data.errors.slice(0, 20).map((log, i) => {
                  // Extract mission ID from message [mission-xxx]
                  const missionMatch = log.message.match(/\[(mission-[^\]]+)\]/)
                  const missionId = missionMatch?.[1]
                  return (
                    <div key={`err-${i}`} className="rounded border border-red-800/40 bg-red-950/20 px-3 py-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                            log.source === 'stage_failed' ? 'bg-red-800 text-red-200' :
                            log.source === 'mission_failed' ? 'bg-red-900 text-red-100' :
                            'bg-orange-800 text-orange-200'
                          }`}>{log.source}</span>
                          {missionId && (
                            <a href={`/missions/${missionId}`}
                               className="font-mono text-[11px] text-blue-400 hover:underline">
                              {missionId.length > 28 ? missionId.slice(0, 28) + '…' : missionId}
                            </a>
                          )}
                        </div>
                        <span className="text-[10px] text-gray-500">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-red-300/80">{log.message}</p>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {logs.data.mutations.length > 0 && (
            <section>
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
                Mutation Audit Trail ({logs.data.totalMutations})
              </h2>
              <div className="space-y-1">
                {logs.data.mutations.slice(0, 15).map((log, i) => (
                  <div key={`mut-${i}`} className="flex items-center justify-between rounded border border-gray-700/30 bg-gray-800/30 px-3 py-1.5">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="rounded bg-blue-800 px-1.5 py-0.5 text-[10px] font-medium text-blue-200">
                        {log.source}
                      </span>
                      <span className="text-gray-300">{log.message}</span>
                    </div>
                    <span className="text-[10px] text-gray-500">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
