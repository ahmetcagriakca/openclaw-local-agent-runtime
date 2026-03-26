/**
 * StageTimeline — horizontal pipeline of mission stages.
 * Gate results: passed → green, failed → red + finding count.
 */
import type { StageDetail } from '../types/api'

const STAGE_STATUS_COLOR: Record<string, string> = {
  passed: 'border-green-500 bg-green-950/50 text-green-300',
  completed: 'border-green-500 bg-green-950/50 text-green-300',
  failed: 'border-red-500 bg-red-950/50 text-red-300',
  running: 'border-indigo-500 bg-indigo-950/50 text-indigo-300',
  paused: 'border-yellow-500 bg-yellow-950/50 text-yellow-300',
  pending: 'border-gray-600 bg-gray-800/50 text-gray-400',
  skipped: 'border-gray-700 bg-gray-900/50 text-gray-500',
}

interface StageTimelineProps {
  stages: StageDetail[]
  activeIndex: number | null
  onSelect: (index: number) => void
}

export function StageTimeline({ stages, activeIndex, onSelect }: StageTimelineProps) {
  if (stages.length === 0) {
    return <div className="py-4 text-center text-gray-500">No stages yet</div>
  }

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {stages.map((stage, i) => {
        const statusClass =
          STAGE_STATUS_COLOR[stage.status] ?? STAGE_STATUS_COLOR['pending']
        const isActive = activeIndex === stage.index
        const gateOk = stage.gateResults?.passed
        const gateFail = stage.gateResults && !stage.gateResults.passed

        return (
          <div key={stage.index} className="flex items-center">
            {i > 0 && (
              <div className={`mx-0.5 h-0.5 w-4 ${
                stage.status === 'running' ? 'bg-indigo-500' :
                stage.status === 'completed' || stage.status === 'passed' ? 'bg-green-600' :
                'bg-gray-600'
              }`} />
            )}
            <button
              onClick={() => onSelect(stage.index)}
              className={`relative flex flex-col items-center rounded-lg border-2 px-3 py-2 text-xs transition ${statusClass} ${
                isActive ? 'ring-2 ring-blue-400' : ''
              } ${stage.status === 'running' ? 'animate-pulse' : ''}`}
            >
              {stage.status === 'running' && (
                <span className="absolute -right-1 -top-1 flex h-3 w-3">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-75" />
                  <span className="relative inline-flex h-3 w-3 rounded-full bg-indigo-500" />
                </span>
              )}
              <span className="font-medium capitalize">
                {stage.role || `Stage ${stage.index}`}
              </span>
              <span className="mt-0.5 text-[10px] opacity-70">{stage.status}</span>
              {stage.agentUsed && (
                <span className="mt-0.5 text-[10px] opacity-50">{stage.agentUsed}</span>
              )}
              <div className="mt-1 flex gap-1">
                {gateOk && <span className="text-green-400" title="Gate passed">✓</span>}
                {gateFail && (
                  <span className="text-red-400" title={`Gate failed — ${stage.gateResults?.findings.length ?? 0} finding(s)`}>
                    ✗ {stage.gateResults?.findings.length ?? 0}
                  </span>
                )}
                {stage.isRework && (
                  <span className="text-orange-400" title={`Rework cycle ${stage.reworkCycle}`}>↻</span>
                )}
              </div>
            </button>
          </div>
        )
      })}
    </div>
  )
}
