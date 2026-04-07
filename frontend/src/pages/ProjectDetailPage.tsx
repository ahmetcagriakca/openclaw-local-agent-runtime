/**
 * ProjectDetailPage — D-145 Faz 2B: Project detail view.
 * Shows project info, linked missions with status badges, published artifacts, rollup summary.
 */
import { useCallback, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { getProject, getProjectRollup, getProjectArtifacts, createMission, updateProject } from '../api/client'
import { usePolling } from '../hooks/usePolling'

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-500',
  active: 'bg-green-600',
  paused: 'bg-yellow-600',
  completed: 'bg-blue-600',
  archived: 'bg-purple-600',
  cancelled: 'bg-red-600',
}

const MISSION_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-500',
  planning: 'bg-blue-500',
  executing: 'bg-indigo-600',
  completed: 'bg-green-600',
  failed: 'bg-red-600',
  aborted: 'bg-orange-600',
  timed_out: 'bg-yellow-600',
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString()
}

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [showMissionForm, setShowMissionForm] = useState(false)
  const [missionGoal, setMissionGoal] = useState('')
  const [missionComplexity, setMissionComplexity] = useState('medium')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editPath, setEditPath] = useState('')
  const [saving, setSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  const projectFetcher = useCallback(() => getProject(id!), [id])
  const rollupFetcher = useCallback(() => getProjectRollup(id!), [id])
  const artifactsFetcher = useCallback(() => getProjectArtifacts(id!), [id])

  const { data: projectData, loading: projectLoading, error: projectError } = usePolling(projectFetcher)
  const { data: rollupData } = usePolling(rollupFetcher)
  const { data: artifactsData } = usePolling(artifactsFetcher)

  if (projectLoading && !projectData) {
    return <p className="text-sm text-gray-400">Loading project...</p>
  }

  if (projectError) {
    return <p className="text-sm text-red-400">Error: {projectError.message}</p>
  }

  const project = projectData?.data?.project
  const missionSummary = projectData?.data?.mission_summary
  const rollup = rollupData?.data
  const artifacts = artifactsData?.data ?? []

  const canCreateMission = project?.status === 'draft' || project?.status === 'active'
  const canEdit = project?.status === 'draft' || project?.status === 'active' || project?.status === 'paused'

  function startEditing() {
    if (!project) return
    setEditName(project.name)
    setEditDesc(project.description || '')
    setEditPath(project.local_path || '')
    setEditError(null)
    setEditing(true)
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault()
    if (!id || !editName.trim()) return
    setSaving(true)
    setEditError(null)
    try {
      const updates: Record<string, string> = {}
      if (editName.trim() !== project?.name) updates.name = editName.trim()
      if (editDesc.trim() !== (project?.description || '')) updates.description = editDesc.trim()
      if (editPath.trim() !== (project?.local_path || '')) updates.local_path = editPath.trim()
      if (Object.keys(updates).length > 0) {
        await updateProject(id, updates)
      }
      setEditing(false)
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  async function handleCreateMission(e: React.FormEvent) {
    e.preventDefault()
    if (!missionGoal.trim() || !id) return
    setCreating(true)
    setCreateError(null)
    try {
      const resp = await createMission(missionGoal.trim(), missionComplexity, id)
      setMissionGoal('')
      setShowMissionForm(false)
      navigate(`/missions/${resp.missionId}`)
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Mission creation failed')
    } finally {
      setCreating(false)
    }
  }

  if (!project) {
    return <p className="text-sm text-gray-400">Project not found.</p>
  }

  return (
    <div>
      {/* Back link */}
      <Link to="/projects" className="mb-4 inline-block text-xs text-blue-400 hover:text-blue-300">
        &larr; All Projects
      </Link>

      {/* Project Header */}
      <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-100">{project.name}</h2>
            {project.description && (
              <p className="mt-1 text-sm text-gray-400">{project.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {canEdit && (
              <button
                onClick={startEditing}
                className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-500"
              >
                Edit
              </button>
            )}
            {canCreateMission && (
              <button
                onClick={() => setShowMissionForm(!showMissionForm)}
                className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-500"
              >
                + New Mission
              </button>
            )}
            <span
              className={`rounded px-3 py-1 text-xs font-medium text-white ${STATUS_COLORS[project.status] ?? 'bg-gray-600'}`}
            >
              {project.status}
            </span>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
          <span>Owner: {project.owner}</span>
          <span>Created: {formatDate(project.created_at)}</span>
          <span>Updated: {formatDate(project.updated_at)}</span>
          <span>ID: {project.project_id}</span>
        </div>
        {project.local_path && (
          <div className="mt-2 rounded bg-gray-800 px-3 py-1.5 text-xs font-mono text-gray-300">
            Path: {project.local_path}
          </div>
        )}
      </div>

      {/* Edit Project Form */}
      {editing && (
        <div className="mb-6 rounded-lg border border-blue-800 bg-gray-900 p-4">
          <h3 className="mb-3 text-sm font-medium text-blue-400">Edit Project</h3>
          <form onSubmit={handleSaveEdit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Project Name</label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Description</label>
              <textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 focus:border-blue-500 focus:outline-none"
                rows={2}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Local Path</label>
              <input
                type="text"
                value={editPath}
                onChange={(e) => setEditPath(e.target.value)}
                placeholder="C:\Users\AKCA\my-project"
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm font-mono text-gray-100 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
              />
              <p className="mt-1 text-[10px] text-gray-500">Directory must exist on disk.</p>
            </div>
            {editError && <p className="text-xs text-red-400">{editError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={saving || !editName.trim()}
                className="rounded bg-blue-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-blue-500 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="rounded bg-gray-700 px-4 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Create Mission Form */}
      {showMissionForm && canCreateMission && (
        <div className="mb-6 rounded-lg border border-green-800 bg-gray-900 p-4">
          <h3 className="mb-3 text-sm font-medium text-green-400">Create Mission for {project.name}</h3>
          <form onSubmit={handleCreateMission} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Mission Goal</label>
              <textarea
                value={missionGoal}
                onChange={(e) => setMissionGoal(e.target.value)}
                placeholder="Describe what this mission should accomplish..."
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none"
                rows={3}
                maxLength={2000}
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Complexity</label>
              <select
                value={missionComplexity}
                onChange={(e) => setMissionComplexity(e.target.value)}
                className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-100 focus:border-green-500 focus:outline-none"
              >
                <option value="trivial">Trivial</option>
                <option value="simple">Simple</option>
                <option value="medium">Medium</option>
                <option value="complex">Complex</option>
              </select>
            </div>
            {createError && (
              <p className="text-xs text-red-400">{createError}</p>
            )}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating || !missionGoal.trim()}
                className="rounded bg-green-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Launch Mission'}
              </button>
              <button
                type="button"
                onClick={() => setShowMissionForm(false)}
                className="rounded bg-gray-700 px-4 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rollup Summary */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <div className="text-2xl font-bold text-gray-100">{rollup?.total_missions ?? missionSummary?.total ?? 0}</div>
          <div className="text-xs text-gray-400">Total Missions</div>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <div className="text-2xl font-bold text-green-400">{rollup?.active_count ?? missionSummary?.active_count ?? 0}</div>
          <div className="text-xs text-gray-400">Active</div>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <div className="text-2xl font-bold text-blue-400">{rollup?.quiescent_count ?? missionSummary?.quiescent_count ?? 0}</div>
          <div className="text-xs text-gray-400">Quiescent</div>
        </div>
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
          <div className="text-2xl font-bold text-gray-300">{rollup?.total_tokens?.toLocaleString() ?? '-'}</div>
          <div className="text-xs text-gray-400">Total Tokens</div>
        </div>
      </div>

      {/* Status breakdown */}
      {rollup?.by_status && Object.keys(rollup.by_status).length > 0 && (
        <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
          <h3 className="mb-2 text-sm font-medium text-gray-300">Missions by Status</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(rollup.by_status).map(([status, count]) => (
              <span
                key={status}
                className={`rounded px-2 py-1 text-xs text-white ${MISSION_STATUS_COLORS[status] ?? 'bg-gray-600'}`}
              >
                {status}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Published Artifacts */}
      <div className="mb-6 rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-gray-300">Published Artifacts ({artifacts.length})</h3>
        {artifacts.length === 0 ? (
          <p className="text-xs text-gray-500">No published artifacts.</p>
        ) : (
          <div className="space-y-1">
            {artifacts.map((a) => (
              <div key={a.artifact_id} className="flex items-center justify-between rounded bg-gray-800 px-3 py-2 text-xs">
                <span className="text-gray-200">{a.artifact_id}</span>
                <span className="text-gray-500">
                  mission: {a.mission_id} | {formatDate(a.published_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Last Activity */}
      {rollup?.last_activity && (
        <div className="text-xs text-gray-500">
          Last activity: {formatDate(rollup.last_activity)} | Rollup computed: {formatDate(rollup.computed_at)}
        </div>
      )}
    </div>
  )
}
