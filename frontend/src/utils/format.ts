/**
 * Shared formatting utilities — Sprint 47.
 * Consistent date, number, duration, and cost formatting across all pages.
 */

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return iso
  }
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return '-'
  if (n === 0) return '0'
  return n.toLocaleString()
}

export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`
  return String(tokens)
}

export function formatDuration(ms: number | null | undefined): string {
  if (!ms) return '-'
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`
  if (ms >= 1_000) return `${(ms / 1_000).toFixed(1)}s`
  return `${ms}ms`
}

export function formatCost(cost: number): string {
  if (cost === 0) return '$0'
  return cost < 0.01 ? `$${cost.toFixed(4)}` : `$${cost.toFixed(2)}`
}
