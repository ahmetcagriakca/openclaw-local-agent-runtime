/**
 * ProjectsPage — D-145 Faz 2B: Project list view.
 * Shows all projects with status, mission count, last activity.
 * Filterable by status, sortable.
 */
import { useState, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { getProjects } from '../api/client'
import { usePolling } from '../hooks/usePolling'
import type { ProjectItem } from '../types/api'

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
  const [statusFilter, setStatusFilter] = useState('all')
  const [sort, setSort] = useState('updated_at_desc')
  const [search, setSearch] = useState('')

  const fetcher = useCallback(() => {
    const params: { status?: string; sort?: string; search?: string } = { sort }
    if (statusFilter !== 'all') params.status = statusFilter
    if (search.trim()) params.search = search.trim()
    return getProjects(params)
  }, [statusFilter, sort, search])

  const { data, loading, error, refresh } = usePolling(fetcher)

  const projects: ProjectItem[] = useMemo(() => data?.data ?? [], [data])
  const total = data?.total ?? 0

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Projects ({total})</h2>
        <button
          onClick={refresh}
          className="rounded bg-gray-700 px-3 py-1.5 text-xs text-gray-200 hover:bg-gray-600"
        >
          Refresh
        </button>
      </div>

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
        <p className="text-sm text-red-400">Error: {error.message}</p>
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
