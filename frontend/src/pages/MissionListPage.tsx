/**
 * MissionListPage — lists all missions with polling + SSE invalidation.
 * Empty/loading/error states explicit. Silent absence forbidden.
 * New Mission form for creating missions from the dashboard.
 */
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getMissions, createMission } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { MissionStateBadge } from '../components/MissionStateBadge'
import { ApiErrorBanner } from '../components/ApiErrorBanner'

export function MissionListPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getMissions, 10_000)
  const [showCreate, setShowCreate] = useState(false)
  const [goal, setGoal] = useState('')
  const [complexity, setComplexity] = useState('medium')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const stateFilter = searchParams.get('state') ?? 'all'
  const setStateFilter = (v: string) => {
    if (v === 'all') { setSearchParams({}) }
    else { setSearchParams({ state: v }) }
  }

  // SSE: immediate refresh on mission changes
  useSSEInvalidation(['mission_list_changed', 'mission_updated'], refresh)

  const handleCreate = async () => {
    if (!goal.trim()) return
    setCreating(true)
    setCreateError(null)
    try {
      const result = await createMission(goal.trim(), complexity)
      setToast(`Mission created: ${result.missionId}`)
      setGoal('')
      setShowCreate(false)
      setTimeout(() => setToast(null), 5000)
      refresh()
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Failed to create mission')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Missions</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCreate(!showCreate)}
            title={showCreate ? 'Close form' : 'New Mission'}
            className="rounded bg-green-700 p-1.5 text-white hover:bg-green-600"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {showCreate
                ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                : <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />}
            </svg>
          </button>
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
      </div>

      {/* Create Mission Form */}
      {showCreate && (
        <div className="rounded-lg border border-green-700/50 bg-green-950/20 p-4">
          <h2 className="mb-3 text-sm font-semibold text-green-300">Create New Mission</h2>
          <div className="space-y-3">
            <div>
              <label htmlFor="mission-goal" className="mb-1 block text-xs text-gray-400">
                Mission Goal
              </label>
              <textarea
                id="mission-goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="Describe what you want the agents to accomplish..."
                rows={3}
                className="w-full rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
              />
            </div>
            <div>
              <label htmlFor="mission-complexity" className="mb-1 block text-xs text-gray-400">
                Complexity
              </label>
              <select
                id="mission-complexity"
                value={complexity}
                onChange={(e) => setComplexity(e.target.value)}
                className="rounded border border-gray-600 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-green-500 focus:outline-none"
              >
                <option value="trivial">Trivial — Analyst → Developer → Tester</option>
                <option value="simple">Simple — + Reviewer</option>
                <option value="medium">Medium — + PO, Architect, Manager</option>
                <option value="complex">Complex — Full 9-role pipeline</option>
              </select>
            </div>
            {createError && (
              <p className="text-sm text-red-400">{createError}</p>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !goal.trim()}
                className="flex items-center gap-2 rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-500 disabled:opacity-50"
              >
                {creating && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                )}
                {creating ? 'Creating...' : 'Launch Mission'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="rounded px-3 py-2 text-sm text-gray-400 hover:bg-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* State Filter */}
      {data && data.missions.length > 0 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Filter:</span>
          {['all', 'pending', 'planning', 'executing', 'completed', 'failed'].map((f) => (
            <button
              key={f}
              onClick={() => setStateFilter(f)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                stateFilter === f
                  ? f === 'failed' ? 'bg-red-700 text-white'
                    : f === 'completed' ? 'bg-green-700 text-white'
                    : 'bg-blue-700 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {f === 'all' ? `All (${data.missions.length})` : f}
            </button>
          ))}
        </div>
      )}

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
          Loading missions…
        </div>
      )}

      {error && (
        <ApiErrorBanner error={error} onRetry={refresh} />
      )}

      {data && data.missions.length === 0 && !showCreate && (
        <div className="py-8 text-center text-gray-500">
          <p>No missions found</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 rounded bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-600"
          >
            Create your first mission
          </button>
        </div>
      )}

      {data && data.missions.length > 0 && (() => {
        const filtered = stateFilter === 'all'
          ? data.missions
          : data.missions.filter((m) => m.state === stateFilter)
        return filtered.length === 0 ? (
          <div className="py-6 text-center text-gray-500">
            No missions matching filter "{stateFilter}"
          </div>
        ) : (
        <div className="space-y-2">
          {filtered.map((m) => (
            <Link
              key={m.missionId}
              to={`/missions/${m.missionId}`}
              className="block rounded-lg border border-gray-700/50 bg-gray-800/50 p-4 transition hover:border-gray-600 hover:bg-gray-800"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-gray-300">
                    {m.missionId.length > 24
                      ? `${m.missionId.slice(0, 24)}…`
                      : m.missionId}
                  </span>
                  <MissionStateBadge state={m.state} />
                  <DataQualityBadge quality={m.dataQuality} />
                </div>
                <div className="text-xs text-gray-500">
                  {m.stageCount > 0 && (
                    <span>Stage {m.currentStage}/{m.stageCount}</span>
                  )}
                </div>
              </div>
              {m.goal && (
                <p className="mt-1 text-sm text-gray-400 line-clamp-2">
                  {m.goal}
                </p>
              )}
              <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
                {m.startedAt && <span>Started: {new Date(m.startedAt).toLocaleString()}</span>}
                {m.stageSummary && <span>{m.stageSummary}</span>}
              </div>
            </Link>
          ))}
        </div>
        )
      })()}

      {/* Success toast */}
      {toast && (
        <div className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-lg border border-green-600/50 bg-green-950/90 px-4 py-3 text-sm font-medium text-green-300 shadow-lg">
          <span>{toast}</span>
          <button onClick={() => setToast(null)} className="ml-2 text-xs opacity-70 hover:opacity-100">✕</button>
        </div>
      )}
    </div>
  )
}
