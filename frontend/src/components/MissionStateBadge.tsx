/**
 * MissionStateBadge — FSM state visual badge.
 */

const STATE_COLORS: Record<string, string> = {
  pending: 'bg-gray-600 text-gray-200',
  planning: 'bg-blue-600 text-white',
  executing: 'bg-indigo-600 text-white',
  gate_check: 'bg-yellow-600 text-gray-900',
  rework: 'bg-orange-600 text-white',
  approval_wait: 'bg-purple-600 text-white',
  completed: 'bg-green-600 text-white',
  failed: 'bg-red-600 text-white',
  aborted: 'bg-red-800 text-gray-200',
  timed_out: 'bg-red-700 text-gray-200',
}

interface MissionStateBadgeProps {
  state: string
}

export function MissionStateBadge({ state }: MissionStateBadgeProps) {
  const color = STATE_COLORS[state] ?? 'bg-gray-600 text-gray-300'
  const label = state.replace(/_/g, ' ')

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${color}`}
    >
      {label}
    </span>
  )
}
