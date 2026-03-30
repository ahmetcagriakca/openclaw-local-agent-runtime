/**
 * AgentHealthPage — B-108: Agent health / capability view.
 * Shows provider liveness, role capability matrix, and per-role performance.
 */
import { getProviders, getAgentRoles, getCapabilityMatrix, getAgentPerformance } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { DataQualityBadge } from '../components/DataQualityBadge'

const PROVIDER_STATUS: Record<string, { color: string; dot: string; label: string }> = {
  ok: { color: 'bg-green-600 text-white', dot: 'bg-green-500', label: 'Online' },
  unavailable: { color: 'bg-gray-600 text-white', dot: 'bg-gray-500', label: 'Unavailable' },
  error: { color: 'bg-red-600 text-white', dot: 'bg-red-500', label: 'Error' },
  unknown: { color: 'bg-gray-500 text-white', dot: 'bg-gray-500', label: 'Unknown' },
}

const DISCOVERY_COLORS: Record<string, string> = {
  primary: 'bg-blue-800 text-blue-200',
  secondary: 'bg-indigo-800 text-indigo-200',
  forbidden: 'bg-red-800 text-red-200',
  none: 'bg-gray-700 text-gray-300',
}

const TIER_LABELS: Record<number, string> = {
  1: 'Tier 1 (Fast)',
  2: 'Tier 2 (Standard)',
  3: 'Tier 3 (Premium)',
}

export function AgentHealthPage() {
  const providers = usePolling(getProviders, 15_000)
  const roles = usePolling(getAgentRoles, 60_000)
  const matrix = usePolling(getCapabilityMatrix, 60_000)
  const performance = usePolling(getAgentPerformance, 30_000)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Agent Health</h1>
        {providers.data && (
          <div className="flex items-center gap-3">
            <span
              className={`rounded-lg px-4 py-2 text-lg font-bold ${
                PROVIDER_STATUS[providers.data.status]?.color ?? PROVIDER_STATUS['unknown']!.color
              }`}
            >
              {providers.data.available_count}/{providers.data.total_count} Providers
            </span>
            <DataQualityBadge quality={providers.data.meta.dataQuality} />
          </div>
        )}
      </div>

      {/* Provider Cards */}
      <section>
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
          LLM Providers
        </h2>

        {providers.loading && !providers.data && (
          <div className="flex items-center gap-2 py-4 text-gray-400">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
            Loading providers...
          </div>
        )}

        {providers.data && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {providers.data.providers.map((p) => {
              const cfg = PROVIDER_STATUS[p.status] ?? PROVIDER_STATUS['unknown']!
              return (
                <div
                  key={p.provider}
                  className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`inline-block h-3 w-3 rounded-full ${cfg.dot}`} />
                      <span className="text-sm font-medium text-gray-100">{p.name}</span>
                    </div>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${cfg.color}`}
                    >
                      {cfg.label}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-gray-400">{p.detail}</p>
                  <p className="mt-1 text-[10px] text-gray-600">Model: {p.model}</p>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Capability Matrix */}
      {matrix.data && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Role-Provider Capability Matrix
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50 text-left text-xs text-gray-500">
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Preferred Model</th>
                  <th className="px-3 py-2">Tier</th>
                  <th className="px-3 py-2">Tool Policy</th>
                  <th className="px-3 py-2 text-right">Tools</th>
                  <th className="px-3 py-2">Discovery</th>
                  <th className="px-3 py-2 text-center">Expand</th>
                </tr>
              </thead>
              <tbody>
                {matrix.data.matrix.map((entry) => (
                  <tr
                    key={entry.role}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30"
                  >
                    <td className="px-3 py-2">
                      <span className="font-medium text-gray-100">{entry.displayName}</span>
                      <span className="ml-2 text-[10px] text-gray-500">{entry.role}</span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-300">{entry.preferredModel}</td>
                    <td className="px-3 py-2 text-xs text-gray-400">
                      {TIER_LABELS[entry.modelTier] ?? `Tier ${entry.modelTier}`}
                    </td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-gray-700 px-2 py-0.5 text-[10px] font-medium text-gray-300">
                        {entry.toolPolicy}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-gray-400">{entry.toolCount}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                          DISCOVERY_COLORS[entry.discoveryRights] ?? DISCOVERY_COLORS['none']!
                        }`}
                      >
                        {entry.discoveryRights}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      {entry.canExpand ? (
                        <span className="text-green-400">Yes</span>
                      ) : (
                        <span className="text-gray-500">No</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Agent Roles Detail */}
      {roles.data && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Agent Roles ({roles.data.total})
          </h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {roles.data.roles.map((role) => (
              <div
                key={role.id}
                className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-4"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-100">{role.displayName}</span>
                  <span className="rounded bg-gray-700 px-2 py-0.5 text-[10px] font-medium text-gray-300">
                    {role.toolPolicy}
                  </span>
                </div>
                <div className="mt-2 space-y-1 text-xs text-gray-400">
                  <p>Model: {role.preferredModel} (Tier {role.defaultModelTier})</p>
                  <p>Default Skill: {role.defaultSkill}</p>
                  <p>Tools: {role.toolCount} allowed</p>
                  {role.maxFileReads > 0 && (
                    <p>
                      File reads: {role.maxFileReads}, Dir reads: {role.maxDirectoryReads}
                    </p>
                  )}
                </div>
                {role.allowedSkills.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {role.allowedSkills.map((skill) => (
                      <span
                        key={skill}
                        className="rounded bg-gray-700/70 px-1.5 py-0.5 text-[10px] text-gray-300"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Role Performance */}
      {performance.data && performance.data.performance.length > 0 && (
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-gray-500">
            Role Performance
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700/50 text-left text-xs text-gray-500">
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2 text-right">Missions</th>
                  <th className="px-3 py-2 text-right">Stages</th>
                  <th className="px-3 py-2 text-right">Tool Calls</th>
                  <th className="px-3 py-2 text-right">Reworks</th>
                  <th className="px-3 py-2 text-right">Rework Rate</th>
                  <th className="px-3 py-2 text-right">Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                {performance.data.performance.map((p) => (
                  <tr
                    key={p.role}
                    className="border-b border-gray-800/50 hover:bg-gray-800/30"
                  >
                    <td className="px-3 py-2 font-medium text-gray-100">{p.role}</td>
                    <td className="px-3 py-2 text-right text-gray-300">{p.missions}</td>
                    <td className="px-3 py-2 text-right text-gray-400">{p.stages}</td>
                    <td className="px-3 py-2 text-right text-gray-400">{p.tool_calls}</td>
                    <td className="px-3 py-2 text-right text-gray-400">{p.reworks}</td>
                    <td className="px-3 py-2 text-right">
                      <span
                        className={p.rework_rate > 20 ? 'text-orange-400' : 'text-green-400'}
                      >
                        {p.rework_rate}%
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right text-gray-400">
                      {p.avg_stage_duration_ms > 0
                        ? `${(p.avg_stage_duration_ms / 1000).toFixed(1)}s`
                        : '-'}
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
