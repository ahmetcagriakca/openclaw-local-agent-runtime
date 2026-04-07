/**
 * FreshnessIndicator — freshness + source status.
 * Shows human-readable age, stale threshold warning, source list.
 */
import { useCallback, useEffect, useRef } from 'react'
import type { SourceInfo } from '../types/api'

function formatAge(ms: number): string {
  if (ms < 1000) return `${ms}ms ago`
  const s = Math.round(ms / 1000)
  if (s < 60) return `${s}s ago`
  const m = Math.round(s / 60)
  if (m < 60) return `${m}m ago`
  const h = Math.round(m / 60)
  return `${h}h ago`
}

function PollAge({ lastFetchedAt }: { lastFetchedAt: Date | null }) {
  const spanRef = useRef<HTMLSpanElement>(null)

  const update = useCallback(() => {
    if (!spanRef.current || !lastFetchedAt) return
    spanRef.current.textContent = `Polled ${formatAge(Date.now() - lastFetchedAt.getTime())}`
  }, [lastFetchedAt])

  useEffect(() => {
    update()
    const id = setInterval(update, 5_000)
    return () => clearInterval(id)
  }, [update])

  if (!lastFetchedAt) return null
  return <span ref={spanRef} className="ml-auto text-gray-500" />
}

interface FreshnessIndicatorProps {
  freshnessMs: number
  staleThresholdMs?: number
  sourcesUsed: SourceInfo[]
  sourcesMissing: string[]
  lastFetchedAt: Date | null
}

export function FreshnessIndicator({
  freshnessMs,
  staleThresholdMs,
  sourcesUsed,
  sourcesMissing,
  lastFetchedAt,
}: FreshnessIndicatorProps) {
  const isStale = staleThresholdMs != null && freshnessMs > staleThresholdMs

  return (
    <div
      className={`flex flex-wrap items-center gap-3 rounded px-3 py-1.5 text-xs ${
        isStale
          ? 'border border-red-500/50 bg-red-950/30 text-red-300'
          : 'bg-gray-800/50 text-gray-400'
      }`}
    >
      <span className="font-medium">
        Data age: <span className={isStale ? 'text-red-400' : 'text-gray-200'}>{formatAge(freshnessMs)}</span>
      </span>

      {sourcesUsed.length > 0 && (
        <span className="flex items-center gap-1">
          <span className="text-green-400">●</span>
          {sourcesUsed.map((s) => s.name).join(', ')}
        </span>
      )}

      {sourcesMissing.length > 0 && (
        <span className="flex items-center gap-1">
          <span className="text-red-400">●</span>
          Missing: {sourcesMissing.join(', ')}
        </span>
      )}

      <PollAge lastFetchedAt={lastFetchedAt} />
    </div>
  )
}
