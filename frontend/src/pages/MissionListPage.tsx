/**
 * MissionListPage — lists all missions with polling + SSE invalidation.
 * Empty/loading/error states explicit. Silent absence forbidden.
 * New Mission form for creating missions from the dashboard.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { getMissions, createMission } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import { useSSEInvalidation } from '../hooks/SSEContext'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { MissionStateBadge } from '../components/MissionStateBadge'

export function MissionListPage() {
  const { data, error, loading, refresh, lastFetchedAt } = usePolling(getMissions)
  const [showCreate, setShowCreate] = useState(false)
  const [goal, setGoal] = useState('')
  const [complexity, setComplexity] = useState('medium')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

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
            className="rounded bg-green-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-600"
          >
            {showCreate ? 'Close' : '+ New Mission'}
          </button>
          <button
            onClick={refresh}
            className="rounded bg-gray-700 px-3 py-1.5 text-sm hover:bg-gray-600"
          >
            Refresh
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
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load missions</p>
          <p className="mt-1 text-sm">{error.message}</p>
          <button
            onClick={refresh}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
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

      {data && data.missions.length > 0 && (
        <div className="space-y-2">
          {data.missions.map((m) => (
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
      )}

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
