/**
 * CostDashboardPage — B-105: Cost/outcome dashboard.
 * Shows cost summary KPIs, provider breakdown, per-mission costs, and trends.
 */
import { useState } from 'react'
import { getCostSummary, getCostMissions, getCostTrends } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { DataQualityBadge } from '../components/DataQualityBadge'

const STATUS_COLORS: Record<string, string> = {
  completed: 'bg-green-600',
  failed: 'bg-red-600',
  aborted: 'bg-orange-600',
  timed_out: 'bg-yellow-600',
}

function formatCost(cost: number): string {
  return cost < 0.01 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`
}

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`
  return String(tokens)
}

function formatDuration(ms: number): string {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`
  return `${(ms / 1000).toFixed(1)}s`
}

export function CostDashboardPage() {
  const [trendBucket, setTrendBucket] = useState<string>('daily')
  const summary = usePolling(getCostSummary, 30_000)
  const missions = usePolling(getCostMissions, 30_000)
  const trends = usePolling(() => getCostTrends(trendBucket), 60_000)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Cost & Outcomes</h1>
        {summary.data && <DataQualityBadge quality={summary.data.meta.dataQuality} />}
      </div>

      {summary.loading && !summary.data && (
        <div className="flex items-center gap-2 py-8 text-gray-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
          Loading cost data...
        </div>
      )}

      {summary.error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load cost data</p>
          <p className="mt-1 text-sm">{summary.error.message}</p>
        </div>
      )}

      {summary.data && (
        <>
          {/* KPI Cards */}
          <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <KpiCard
              label="Total Cost (Est.)"
              value={formatCost(summary.data.total_estimated_cost)}
              sub={`${summary.data.total_missions} missions`}
              accent="text-emerald-400"
            />
            <KpiCard
              label="Avg Cost / Mission"
              value={formatCost(summary.data.avg_cost_per_mission)}
              sub={`${formatTokens(summary.data.avg_tokens_per_completed)} avg tokens`}
              accent="text-blue-400"
            />
            <KpiCard
              label="Success Rate"
              value={`${summary.data.success_rate}%`}
              sub={`${summary.data.completed} / ${summary.data.total_missions}`}
              accent={summary.data.success_rate >= 80 ? 'text-green-400' : 'text-orange-400'}
            />
            <KpiCard
              label="Total Tokens"
              value={formatTokens(summary.data.total_tokens)}
              sub={`${summary.data.total_tool_calls} tool calls`}
              accent="text-purple-400"
            />
          </section>

          {/* Provider Breakdown */}
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
              Provider Breakdown
            </h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(summary.data.provider_breakdown).map(([provider, data]) => (
                <div
                  key={provider}
                  className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-100">{provider}</span>
                    <span className="text-sm font-bold text-emerald-400">
                      {formatCost(data.estimated_cost)}
                    </span>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-gray-400">
                    <span>{formatTokens(data.tokens)} tokens</span>
                    <span>{data.missions} missions</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Outcome Stats */}
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
              Outcome Metrics
            </h2>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
                <p className="text-xs text-gray-500">Avg Duration</p>
                <p className="mt-1 text-lg font-bold text-gray-100">
                  {formatDuration(summary.data.avg_duration_ms)}
                </p>
              </div>
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
                <p className="text-xs text-gray-500">Total Reworks</p>
                <p className="mt-1 text-lg font-bold text-gray-100">{summary.data.total_reworks}</p>
              </div>
              <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
                <p className="text-xs text-gray-500">Budget Events</p>
                <p className="mt-1 text-lg font-bold text-gray-100">
                  {summary.data.total_budget_events}
                </p>
              </div>
            </div>
          </section>
        </>
      )}

      {/* Cost Trends */}
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-500">
            Cost Trends
          </h2>
          <div className="flex gap-1">
            {(['daily', 'weekly', 'monthly'] as const).map((b) => (
              <button
                key={b}
                onClick={() => setTrendBucket(b)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                  trendBucket === b
                    ? 'bg-gray-700 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'
                }`}
              >
                {b.charAt(0).toUpperCase() + b.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {trends.data && trends.data.trends.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50 text-left text-xs text-gray-500">
                  <th className="px-3 py-2">Period</th>
                  <th className="px-3 py-2 text-right">Cost</th>
                  <th className="px-3 py-2 text-right">Tokens</th>
                  <th className="px-3 py-2 text-right">Missions</th>
                  <th className="px-3 py-2 text-right">Success</th>
                </tr>
              </thead>
              <tbody>
                {trends.data.trends.map((t) => (
                  <tr key={t.period} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="px-3 py-2 font-mono text-xs text-gray-300">{t.period}</td>
                    <td className="px-3 py-2 text-right font-medium text-emerald-400">
                      {formatCost(t.estimated_cost)}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-400">{formatTokens(t.tokens)}</td>
                    <td className="px-3 py-2 text-right text-gray-400">{t.missions}</td>
                    <td className="px-3 py-2 text-right">
                      <span
                        className={
                          t.success_rate >= 80 ? 'text-green-400' : 'text-orange-400'
                        }
                      >
                        {t.success_rate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {trends.data && trends.data.trends.length === 0 && (
          <p className="py-4 text-center text-sm text-gray-500">No trend data available</p>
        )}
      </section>

      {/* Per-Mission Cost Table */}
      {missions.data && missions.data.missions.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Per-Mission Costs ({missions.data.total})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50 text-left text-xs text-gray-500">
                  <th className="px-3 py-2">Mission</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Provider</th>
                  <th className="px-3 py-2 text-right">Cost</th>
                  <th className="px-3 py-2 text-right">Tokens</th>
                  <th className="px-3 py-2 text-right">Duration</th>
                </tr>
              </thead>
              <tbody>
                {missions.data.missions.slice(0, 25).map((m) => (
                  <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="max-w-[200px] truncate px-3 py-2 text-gray-300">
                      <a
                        href={`/missions/${m.id}`}
                        className="text-blue-400 hover:underline"
                        title={m.goal}
                      >
                        {m.goal || m.id}
                      </a>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold text-white ${
                          STATUS_COLORS[m.status] ?? 'bg-gray-600'
                        }`}
                      >
                        {m.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-400">{m.provider}</td>
                    <td className="px-3 py-2 text-right font-medium text-emerald-400">
                      {formatCost(m.estimated_cost)}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-400">
                      {formatTokens(m.tokens)}
                    </td>
                    <td className="px-3 py-2 text-right text-gray-400">
                      {m.duration_ms > 0 ? formatDuration(m.duration_ms) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

function KpiCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string
  value: string
  sub: string
  accent: string
}) {
  return (
    <div className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${accent}`}>{value}</p>
      <p className="mt-0.5 text-xs text-gray-400">{sub}</p>
    </div>
  )
}
