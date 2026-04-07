/**
 * ProjectsPage — D-145 Faz 2B: Project list view.
 * Shows all projects with status, mission count, last activity.
 * Filterable by status, sortable.
 */
import { useState, useMemo, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getProjects, createProject } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import type { ProjectItem } from '../types/api'
import { ApiErrorBanner } from '../components/ApiErrorBanner'

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-500',
  active: 'bg-green-600',
  paused: 'bg-yellow-600',
  completed: 'bg-blue-600',
  archived: 'bg-purple-600',
  cancelled: 'bg-red-600',
}

const STATUS_OPTIONS = ['all', 'draft', 'active', 'paused', 'completed', 'archived', 'cancelled']
const SORT_OPTIONS = [
  { value: 'updated_at_desc', label: 'Last Updated' },
  { value: 'name_asc', label: 'Name (A-Z)' },
  { value: 'created_at_desc', label: 'Newest First' },
]

function formatRelativeTime(iso: string): string {
  if (!iso) return '-'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function ProjectsPage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState('all')
  const [sort, setSort] = useState('updated_at_desc')
  const [search, setSearch] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newPath, setNewPath] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  const fetcher = useCallback(() => {
    const params: { status?: string; sort?: string; search?: string } = { sort }
    if (statusFilter !== 'all') params.status = statusFilter
    if (search.trim()) params.search = search.trim()
    return getProjects(params)
  }, [statusFilter, sort, search])

  const { data, loading, error, refresh } = usePolling(fetcher)

  const projects: ProjectItem[] = useMemo(() => data?.data ?? [], [data])
  const total = data?.total ?? 0

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    setCreateError(null)
    try {
      const resp = await createProject(newName.trim(), newDesc.trim(), undefined, newPath.trim() || undefined)
      const projectId = (resp.data as { project_id?: string })?.project_id
      setNewName('')
      setNewDesc('')
      setNewPath('')
      setShowCreateForm(false)
      if (projectId) {
        navigate(`/projects/${projectId}`)
      } else {
        refresh()
      }
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Project creation failed')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Projects ({total})</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="rounded bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-500"
          >
            + New Project
          </button>
          <button
            onClick={refresh}
            className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-600"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Create Project Form */}
      {showCreateForm && (
        <div className="mb-4 rounded-lg border border-green-800 bg-gray-900 p-4">
          <h3 className="mb-3 text-sm font-medium text-green-400">Create New Project</h3>
          <form onSubmit={handleCreateProject} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-gray-400">Project Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Enter project name..."
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none"
                required
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Description (optional)</label>
              <textarea
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Describe the project..."
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:border-green-500 focus:outline-none"
                rows={2}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-400">Local Path (project working directory)</label>
              <input
                type="text"
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                placeholder="C:\Users\AKCA\my-project"
                className="w-full rounded border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 font-mono placeholder-gray-500 focus:border-green-500 focus:outline-none"
              />
              <p className="mt-1 text-[10px] text-gray-500">Workspace will use this directory. Leave empty for default.</p>
            </div>
            {createError && <p className="text-xs text-red-400">{createError}</p>}
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={creating || !newName.trim()}
                className="rounded bg-green-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-green-500 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create Project'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreateForm(false)}
                className="rounded bg-gray-700 px-4 py-1.5 text-xs text-gray-300 hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search projects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === 'all' ? 'All statuses' : s}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded border border-gray-700 bg-gray-800 px-3 py-1.5 text-sm text-gray-200"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {loading && !data && (
        <p className="text-sm text-gray-400">Loading projects...</p>
      )}

      {error && (
        <ApiErrorBanner error={error} onRetry={refresh} />
      )}

      {/* Project List */}
      {projects.length === 0 && !loading && (
        <p className="text-sm text-gray-500">No projects found.</p>
      )}

      <div className="space-y-2">
        {projects.map((p) => (
          <Link
            key={p.project_id}
            to={`/projects/${p.project_id}`}
            className="block rounded-lg border border-gray-800 bg-gray-900 p-4 transition hover:border-gray-600 hover:bg-gray-800/80"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="truncate text-sm font-medium text-gray-100">{p.name}</h3>
                  <span
                    className={`inline-block rounded px-2 py-0.5 text-[10px] font-medium text-white ${STATUS_COLORS[p.status] ?? 'bg-gray-600'}`}
                  >
                    {p.status}
                  </span>
                </div>
                {p.description && (
                  <p className="mt-1 truncate text-xs text-gray-400">{p.description}</p>
                )}
              </div>
              <div className="shrink-0 text-right text-xs text-gray-500">
                <div>Owner: {p.owner}</div>
                <div>{formatRelativeTime(p.updated_at)}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
