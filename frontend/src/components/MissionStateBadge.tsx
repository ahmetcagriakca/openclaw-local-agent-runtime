/**
 * MissionStateBadge — FSM state visual badge.
 */

const STATE_COLORS: Record<string, string> = {
  pending: 'bg-gray-600 text-gray-200',
  planning: 'bg-blue-600 text-white',
  executing: 'bg-indigo-600 text-white',
  running: 'bg-indigo-600 text-white',
  gate_check: 'bg-yellow-600 text-gray-900',
  rework: 'bg-orange-600 text-white',
  approval_wait: 'bg-purple-600 text-white',
  paused: 'bg-yellow-700 text-white',
  completed: 'bg-green-600 text-white',
  failed: 'bg-red-600 text-white',
  aborted: 'bg-red-800 text-gray-200',
  timed_out: 'bg-red-700 text-gray-200',
}

const STATE_LABELS: Record<string, string> = {
  pending: 'Pending',
  planning: 'Planning',
  executing: 'Executing',
  running: 'Running',
  gate_check: 'Gate Check',
  rework: 'Rework',
  approval_wait: 'Approval Wait',
  paused: 'Paused',
  completed: 'Completed',
  failed: 'Failed',
  aborted: 'Aborted',
  timed_out: 'Timed Out',
}

const STATE_TOOLTIPS: Record<string, string> = {
  pending: 'Mission queued, not yet started',
  planning: 'LLM generating execution plan',
  executing: 'Stages running',
  running: 'Mission actively executing',
  gate_check: 'Quality gate evaluation in progress',
  rework: 'Stage failed gate, reworking',
  approval_wait: 'Waiting for operator approval',
  paused: 'Mission paused by operator',
  completed: 'All stages completed successfully',
  failed: 'Mission failed with error',
  aborted: 'Mission cancelled by operator',
  timed_out: 'Mission exceeded time limit',
}

interface MissionStateBadgeProps {
  state: string
}

export function MissionStateBadge({ state }: MissionStateBadgeProps) {
  const color = STATE_COLORS[state] ?? 'bg-gray-600 text-gray-300'
  const label = STATE_LABELS[state] ?? state.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const tooltip = STATE_TOOLTIPS[state] ?? state

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}
      title={tooltip}
    >
      {label}
    </span>
  )
}
