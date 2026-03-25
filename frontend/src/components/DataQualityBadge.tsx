/**
 * DataQualityBadge — 6 distinct visual states (D-079).
 * Unknown ≠ zero, missing ≠ healthy, silent absence forbidden.
 */
import { DataQualityStatus } from '../types/api'

const CONFIG: Record<DataQualityStatus, { color: string; icon: string; label: string }> = {
  [DataQualityStatus.Fresh]: {
    color: 'bg-green-600 text-white',
    icon: '✓',
    label: 'Fresh',
  },
  [DataQualityStatus.Partial]: {
    color: 'bg-lime-500 text-gray-900',
    icon: '◐',
    label: 'Partial',
  },
  [DataQualityStatus.Stale]: {
    color: 'bg-orange-500 text-white',
    icon: '⏳',
    label: 'Stale',
  },
  [DataQualityStatus.Degraded]: {
    color: 'bg-red-600 text-white',
    icon: '⚠',
    label: 'Degraded',
  },
  [DataQualityStatus.Unknown]: {
    color: 'bg-gray-500 text-white',
    icon: '?',
    label: 'Unknown',
  },
  [DataQualityStatus.NotReached]: {
    color: 'bg-gray-700 text-gray-300',
    icon: '—',
    label: 'Not Reached',
  },
}

interface DataQualityBadgeProps {
  quality: DataQualityStatus
  detail?: string
  assessedAt?: string
}

export function DataQualityBadge({ quality, detail, assessedAt }: DataQualityBadgeProps) {
  const cfg = CONFIG[quality] ?? CONFIG[DataQualityStatus.Unknown]

  const tooltip = [
    cfg.label,
    detail && `Detail: ${detail}`,
    assessedAt && `Assessed: ${assessedAt}`,
  ]
    .filter(Boolean)
    .join('\n')

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.color}`}
      title={tooltip}
    >
      <span aria-hidden="true">{cfg.icon}</span>
      {cfg.label}
    </span>
  )
}
