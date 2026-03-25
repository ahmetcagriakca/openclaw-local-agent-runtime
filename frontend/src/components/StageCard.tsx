/**
 * StageCard — expanded stage detail view.
 * Shows gate findings, deny forensics, agent info.
 * Deny forensics explicitly visible (never hidden).
 */
import type { StageDetail } from '../types/api'

interface StageCardProps {
  stage: StageDetail
}

export function StageCard({ stage }: StageCardProps) {
  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold capitalize">{stage.role || `Stage ${stage.index}`}</span>
          <span className="rounded bg-gray-700 px-2 py-0.5 text-xs">{stage.status}</span>
          {stage.isRework && (
            <span className="rounded bg-orange-800 px-2 py-0.5 text-xs text-orange-200">
              Rework #{stage.reworkCycle}
            </span>
          )}
          {stage.isRecovery && (
            <span className="rounded bg-yellow-800 px-2 py-0.5 text-xs text-yellow-200">
              Recovery
            </span>
          )}
        </div>
        {stage.agentUsed && (
          <span className="text-xs text-gray-400">
            Model: <span className="text-gray-200">{stage.agentUsed}</span>
          </span>
        )}
      </div>

      {/* Metrics */}
      <div className="flex gap-4 text-xs text-gray-400">
        <span>Tool calls: <span className="text-gray-200">{stage.toolCalls}</span></span>
        <span>Policy denies: <span className="text-gray-200">{stage.policyDenies}</span></span>
        {stage.startedAt && <span>Started: {stage.startedAt}</span>}
        {stage.finishedAt && <span>Finished: {stage.finishedAt}</span>}
      </div>

      {/* Gate Results */}
      {stage.gateResults && (
        <div className={`rounded border p-3 ${
          stage.gateResults.passed
            ? 'border-green-700/50 bg-green-950/30'
            : 'border-red-700/50 bg-red-950/30'
        }`}>
          <div className="flex items-center gap-2 text-sm font-medium">
            {stage.gateResults.passed ? (
              <span className="text-green-400">✓ Gate Passed</span>
            ) : (
              <span className="text-red-400">✗ Gate Failed</span>
            )}
            <span className="text-gray-500">{stage.gateResults.gateName}</span>
          </div>
          {stage.gateResults.findings.length > 0 && (
            <ul className="mt-2 space-y-1 text-xs">
              {stage.gateResults.findings.map((f, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className={
                    f.status === 'pass' ? 'text-green-400' :
                    f.status === 'fail' ? 'text-red-400' :
                    'text-yellow-400'
                  }>
                    {f.status === 'pass' ? '✓' : f.status === 'fail' ? '✗' : '⚠'}
                  </span>
                  <div>
                    <span className="font-medium text-gray-200">{f.check}</span>
                    {f.detail && <span className="ml-1 text-gray-400">— {f.detail}</span>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Deny Forensics — always visible if present */}
      {stage.denyForensics && Object.keys(stage.denyForensics).length > 0 && (
        <div className="rounded border border-amber-700/50 bg-amber-950/30 p-3">
          <h4 className="mb-1 text-sm font-medium text-amber-300">Deny Forensics</h4>
          <pre className="overflow-x-auto text-xs text-amber-200/70">
            {JSON.stringify(stage.denyForensics, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
