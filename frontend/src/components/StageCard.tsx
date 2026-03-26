/**
 * StageCard — expanded stage detail view.
 * Shows error details, gate findings, deny forensics, agent info, LLM result.
 * Error details and deny forensics explicitly visible (never hidden).
 */
import { useState } from 'react'
import type { StageDetail } from '../types/api'

interface StageCardProps {
  stage: StageDetail
}

export function StageCard({ stage }: StageCardProps) {
  const [showResult, setShowResult] = useState(false)
  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [showUserPrompt, setShowUserPrompt] = useState(false)

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/60 p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold capitalize">{stage.role || `Stage ${stage.index}`}</span>
          <span className={`rounded px-2 py-0.5 text-xs font-medium ${
            stage.status === 'completed' ? 'bg-green-800 text-green-200' :
            stage.status === 'failed' ? 'bg-red-800 text-red-200' :
            stage.status === 'running' ? 'bg-blue-800 text-blue-200' :
            'bg-gray-700 text-gray-300'
          }`}>{stage.status}</span>
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
      <div className="flex flex-wrap gap-4 text-xs text-gray-400">
        <span>Tool calls: <span className="text-gray-200">{stage.toolCalls}</span></span>
        <span>Policy denies: <span className="text-gray-200">{stage.policyDenies}</span></span>
        {stage.turnsUsed > 0 && (
          <span>Turns: <span className="text-gray-200">{stage.turnsUsed}</span></span>
        )}
        {stage.durationMs != null && (
          <span>Duration: <span className="text-gray-200">{(stage.durationMs / 1000).toFixed(1)}s</span></span>
        )}
        {stage.startedAt && <span>Started: {new Date(stage.startedAt).toLocaleTimeString()}</span>}
        {stage.finishedAt && <span>Finished: {new Date(stage.finishedAt).toLocaleTimeString()}</span>}
      </div>

      {/* System Prompt — collapsible */}
      {stage.systemPrompt && (
        <div className="rounded border border-purple-700/40 bg-purple-950/20 p-3">
          <button
            onClick={() => setShowSystemPrompt(!showSystemPrompt)}
            className="flex w-full items-center justify-between text-sm font-medium text-purple-300 hover:text-purple-100"
          >
            <span>System Prompt</span>
            <span className="text-xs text-gray-500">{showSystemPrompt ? 'Hide' : 'Show'} ({stage.systemPrompt.length} chars)</span>
          </button>
          {showSystemPrompt && (
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-950/50 p-2 text-xs text-purple-200/80 leading-relaxed">
              {stage.systemPrompt}
            </pre>
          )}
        </div>
      )}

      {/* User Prompt (instruction + context) — collapsible */}
      {stage.userPrompt && (
        <div className="rounded border border-cyan-700/40 bg-cyan-950/20 p-3">
          <button
            onClick={() => setShowUserPrompt(!showUserPrompt)}
            className="flex w-full items-center justify-between text-sm font-medium text-cyan-300 hover:text-cyan-100"
          >
            <span>User Prompt (Instruction + Context)</span>
            <span className="text-xs text-gray-500">{showUserPrompt ? 'Hide' : 'Show'} ({stage.userPrompt.length} chars)</span>
          </button>
          {showUserPrompt && (
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-950/50 p-2 text-xs text-cyan-200/80 leading-relaxed">
              {stage.userPrompt}
            </pre>
          )}
        </div>
      )}

      {/* Error Detail — prominent red box when stage has error */}
      {stage.error && (
        <div className="rounded border border-red-600/60 bg-red-950/40 p-3">
          <h4 className="mb-1 flex items-center gap-2 text-sm font-semibold text-red-400">
            <span>Error Detail</span>
          </h4>
          <pre className="whitespace-pre-wrap break-words text-xs text-red-200/90 leading-relaxed">
            {stage.error}
          </pre>
        </div>
      )}

      {/* Gate Results */}
      {stage.gateResults && (
        <div className={`rounded border p-3 ${
          stage.gateResults.passed
            ? 'border-green-700/50 bg-green-950/30'
            : 'border-red-700/50 bg-red-950/30'
        }`}>
          <div className="flex items-center gap-2 text-sm font-medium">
            {stage.gateResults.passed ? (
              <span className="text-green-400">Gate Passed</span>
            ) : (
              <span className="text-red-400">Gate Failed</span>
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
                    {f.status === 'pass' ? 'PASS' : f.status === 'fail' ? 'FAIL' : 'WARN'}
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
          <pre className="overflow-x-auto whitespace-pre-wrap text-xs text-amber-200/70">
            {JSON.stringify(stage.denyForensics, null, 2)}
          </pre>
        </div>
      )}

      {/* LLM Result — collapsible since it can be long */}
      {stage.result && (
        <div className="rounded border border-gray-600/50 bg-gray-900/40 p-3">
          <button
            onClick={() => setShowResult(!showResult)}
            className="flex w-full items-center justify-between text-sm font-medium text-gray-300 hover:text-gray-100"
          >
            <span>Agent Response</span>
            <span className="text-xs text-gray-500">{showResult ? 'Hide' : 'Show'} ({stage.result.length} chars)</span>
          </button>
          {showResult && (
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap break-words rounded bg-gray-950/50 p-2 text-xs text-gray-300 leading-relaxed">
              {stage.result}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
