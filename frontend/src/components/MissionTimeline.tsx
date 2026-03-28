/**
 * MissionTimeline — visual timeline of mission execution stages.
 * D-119/Phase 7: inspectable automation.
 */
import type { StageDetail } from '../types/api'

interface MissionTimelineProps {
  stages: StageDetail[]
  missionId: string
}

export function MissionTimeline({ stages, missionId }: MissionTimelineProps) {
  if (stages.length === 0) {
    return <div className="text-sm text-gray-500">No stages recorded for {missionId}</div>
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-200">
        Mission Timeline — {missionId}
      </h3>
      <div className="relative border-l-2 border-gray-600 pl-4 space-y-3">
        {stages.map((stage, i) => (
          <div key={i} className="relative">
            <div className={`absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 ${
              stage.status === 'completed' ? 'border-green-500 bg-green-500' :
              stage.status === 'failed' ? 'border-red-500 bg-red-500' :
              stage.status === 'running' ? 'border-blue-500 bg-blue-500 animate-pulse' :
              'border-gray-500 bg-gray-700'
            }`} />
            <div className="rounded border border-gray-700 bg-gray-800/40 p-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-gray-200 capitalize">{stage.role || `Stage ${stage.index}`}</span>
                <span className={`rounded px-1.5 py-0.5 text-[10px] ${
                  stage.status === 'completed' ? 'bg-green-800 text-green-200' :
                  stage.status === 'failed' ? 'bg-red-800 text-red-200' :
                  'bg-gray-700 text-gray-300'
                }`}>{stage.status}</span>
                {stage.durationMs != null && (
                  <span className="text-gray-500">{(stage.durationMs / 1000).toFixed(1)}s</span>
                )}
                {stage.agentUsed && <span className="text-gray-500">{stage.agentUsed}</span>}
              </div>
              {stage.error && (
                <div className="mt-1 text-xs text-red-400">{stage.error}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
