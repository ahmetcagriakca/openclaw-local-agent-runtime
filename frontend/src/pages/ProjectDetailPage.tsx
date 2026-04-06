/**
 * ProjectDetailPage — D-145 Faz 2B: Project detail view.
 * Shows project info, linked missions with status badges, published artifacts, rollup summary.
 */
import { useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getProject, getProjectRollup, getProjectArtifacts } from '../api/client'
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
          <span
            className={`rounded px-3 py-1 text-xs font-medium text-white ${STATUS_COLORS[project.status] ?? 'bg-gray-600'}`}
          >
            {project.status}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500">
          <span>Owner: {project.owner}</span>
          <span>Created: {formatDate(project.created_at)}</span>
          <span>Updated: {formatDate(project.updated_at)}</span>
          <span>ID: {project.project_id}</span>
        </div>
      </div>

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
