/**
 * TemplatesPage — card grid of published mission templates (B-104).
 * Fetches presets (published templates) and displays as cards.
 */
import { useState, useEffect } from 'react'
import type { MissionTemplate } from '../types/api'
import { getPresets } from '../api/client'

export function TemplatesPage() {
  const [templates, setTemplates] = useState<MissionTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchPresets = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getPresets()
      setTemplates(data)
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to load templates'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPresets()
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Templates</h1>
        <button
          onClick={fetchPresets}
          title="Refresh"
          className="rounded bg-gray-700 p-1.5 text-gray-400 hover:bg-gray-600 hover:text-white"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h5M20 20v-5h-5M4.5 15.5A8.5 8.5 0 0118 6.07M19.5 8.5A8.5 8.5 0 016 17.93" />
          </svg>
        </button>
      </div>

      {/* Loading */}
      {loading && templates.length === 0 && (
        <div className="flex items-center gap-2 py-8 text-gray-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-400 border-t-transparent" />
          Loading templates...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
          <p className="font-medium">Failed to load templates</p>
          <p className="mt-1 text-sm">{error.message}</p>
          <button
            onClick={fetchPresets}
            className="mt-2 rounded bg-red-700 px-3 py-1 text-sm hover:bg-red-600"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && templates.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          <p>No published templates available</p>
        </div>
      )}

      {/* Card grid */}
      {templates.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div
              key={t.id}
              className="flex flex-col rounded-lg border border-gray-700/50 bg-gray-800/50 p-4 transition hover:border-gray-600 hover:bg-gray-800"
            >
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-100">{t.name}</h2>
                <span className="rounded bg-blue-700/30 px-2 py-0.5 text-[10px] font-medium text-blue-300">
                  v{t.version}
                </span>
              </div>
              <p className="mb-3 flex-1 text-xs text-gray-400 line-clamp-3">{t.description}</p>
              <div className="mb-3 flex items-center gap-3 text-xs text-gray-500">
                <span>{t.parameters.length} parameter{t.parameters.length !== 1 ? 's' : ''}</span>
                <span>{t.mission_config.specialist}</span>
              </div>
              <button
                className="w-full rounded bg-green-700 px-3 py-2 text-sm font-medium text-white transition hover:bg-green-600"
              >
                Run
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
