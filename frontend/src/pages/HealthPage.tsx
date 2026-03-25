/**
 * HealthPage — health status + capabilities + SSE invalidation.
 * Capability tri-state: available ≠ unavailable ≠ unknown.
 */
import { getHealth, getCapabilities } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { CapabilityStatus } from '../types/api'

const HEALTH_STATUS: Record<string, { color: string; label: string }> = {
  ok: { color: 'bg-green-600 text-white', label: 'Healthy' },
  degraded: { color: 'bg-orange-500 text-white', label: 'Degraded' },
  error: { color: 'bg-red-600 text-white', label: 'Error' },
  unknown: { color: 'bg-gray-500 text-white', label: 'Unknown' },
}

const CAP_STATUS: Record<string, { color: string; icon: string }> = {
  [CapabilityStatus.Available]: { color: 'text-green-400', icon: '✓' },
  [CapabilityStatus.Unavailable]: { color: 'text-red-400', icon: '✗' },
  [CapabilityStatus.Unknown]: { color: 'text-gray-400', icon: '?' },
}

export function HealthPage() {
  const health = usePolling(getHealth)
  const caps = usePolling(getCapabilities)

  // SSE: refresh on health/capability changes
  useSSEInvalidation('health_changed', health.refresh)
  useSSEInvalidation('capability_changed', caps.refresh)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">System Health</h1>

      {/* Health Section */}
      <section className="space-y-3">
        {health.loading && !health.data && (
          <div className="flex items-center gap-2 py-4 text-gray-400">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            Loading health…
          </div>
        )}

        {health.error && (
          <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
            <p className="font-medium">Failed to load health</p>
            <p className="mt-1 text-sm">{health.error.message}</p>
            <button
              onClick={health.refresh}
              className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
            >
              Retry
            </button>
          </div>
        )}

        {health.data && (
          <>
            {/* Overall Status */}
            <div className="flex items-center gap-4">
              <span
                className={`rounded-lg px-4 py-2 text-lg font-bold ${
                  HEALTH_STATUS[health.data.status]?.color ?? HEALTH_STATUS['unknown']!.color
                }`}
              >
                {HEALTH_STATUS[health.data.status]?.label ?? health.data.status}
              </span>
              <DataQualityBadge quality={health.data.meta.dataQuality} />
            </div>

            <FreshnessIndicator
              freshnessMs={health.data.meta.freshnessMs}
              sourcesUsed={health.data.meta.sourcesUsed}
              sourcesMissing={health.data.meta.sourcesMissing}
              lastFetchedAt={health.lastFetchedAt}
            />

            {/* Components */}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(health.data.components).length === 0 && (
                <p className="text-sm text-gray-500 col-span-full">No components reported</p>
              )}
              {Object.entries(health.data.components).map(([key, comp]) => {
                const statusCfg = HEALTH_STATUS[comp.status] ?? HEALTH_STATUS['unknown']!
                return (
                  <div
                    key={key}
                    className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-3"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{comp.name || key}</span>
                      <span className={`rounded-full px-2 py-0.5 text-xs ${statusCfg.color}`}>
                        {statusCfg.label}
                      </span>
                    </div>
                    {comp.detail && (
                      <p className="mt-1 text-xs text-gray-400">{comp.detail}</p>
                    )}
                    {comp.lastCheckAt && (
                      <p className="mt-1 text-[10px] text-gray-500">
                        Last check: {comp.lastCheckAt}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </>
        )}
      </section>

      {/* Capabilities Section */}
      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Capabilities</h2>

        {caps.loading && !caps.data && (
          <div className="flex items-center gap-2 py-4 text-gray-400">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            Loading capabilities…
          </div>
        )}

        {caps.error && (
          <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
            <p className="font-medium">Failed to load capabilities</p>
            <p className="mt-1 text-sm">{caps.error.message}</p>
            <button
              onClick={caps.refresh}
              className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
            >
              Retry
            </button>
          </div>
        )}

        {caps.data && (
          <div className="space-y-2">
            {Object.keys(caps.data.capabilities).length === 0 && (
              <p className="text-sm text-gray-500">No capabilities reported</p>
            )}
            {Object.entries(caps.data.capabilities).map(([key, cap]) => {
              const s = CAP_STATUS[cap.status] ?? CAP_STATUS[CapabilityStatus.Unknown]!
              return (
                <div
                  key={key}
                  className="flex items-center justify-between rounded border border-gray-700/50 bg-gray-800/50 px-4 py-2"
                >
                  <span className="text-sm">{cap.name || key}</span>
                  <span className={`flex items-center gap-1 text-sm font-medium ${s.color}`}>
                    <span>{s.icon}</span>
                    <span className="capitalize">{cap.status}</span>
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
