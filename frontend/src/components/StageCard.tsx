/**
 * StageCard — expanded stage detail view.
 * Shows error details, gate findings, deny forensics, agent info, LLM result.
 * Error details and deny forensics explicitly visible (never hidden).
 */
import { useState, useEffect } from 'react'
import type { StageDetail, RoleInfo } from '../types/api'
import { getRoles } from '../api/client'
import { AgentSkillsPopup } from './AgentSkillsPopup'

/** Module-level roles cache so we only fetch once across all StageCards. */
let _rolesCache: Record<string, RoleInfo> | null = null
let _rolesFetchPromise: Promise<Record<string, RoleInfo>> | null = null

function fetchRolesOnce(): Promise<Record<string, RoleInfo>> {
  if (_rolesCache) return Promise.resolve(_rolesCache)
  if (!_rolesFetchPromise) {
    _rolesFetchPromise = getRoles()
      .then((res) => { _rolesCache = res.roles; return res.roles })
      .catch(() => { _rolesFetchPromise = null; return {} })
  }
  return _rolesFetchPromise
}

interface StageCardProps {
  stage: StageDetail
}

export function StageCard({ stage }: StageCardProps) {
  const [showResult, setShowResult] = useState(false)
  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [showUserPrompt, setShowUserPrompt] = useState(false)
  const [showToolCalls, setShowToolCalls] = useState(false)
  const [showSkillsPopup, setShowSkillsPopup] = useState(false)
  const [roles, setRoles] = useState<Record<string, RoleInfo> | null>(_rolesCache)

  useEffect(() => {
    if (!roles) {
      fetchRolesOnce().then((r) => { if (Object.keys(r).length > 0) setRoles(r) })
    }
  }, [roles])

  const roleInfo = roles && stage.role ? roles[stage.role] : null

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
        <div className="flex items-center gap-2">
          {stage.agentUsed && (
            <span className="text-xs text-gray-400">
              Model: <span className="text-gray-200">{stage.agentUsed}</span>
            </span>
          )}
          {roleInfo && (
            <button
              onClick={() => setShowSkillsPopup(true)}
              className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-indigo-300"
              title={`View ${roleInfo.name} skills & tools`}
              aria-label="View agent skills"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>
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

      {/* Tool Call Details — collapsible */}
      {stage.toolCallDetails && stage.toolCallDetails.length > 0 && (
        <div className="rounded border border-indigo-700/40 bg-indigo-950/20 p-3">
          <button
            onClick={() => setShowToolCalls(!showToolCalls)}
            className="flex w-full items-center justify-between text-sm font-medium text-indigo-300 hover:text-indigo-100"
          >
            <span>Tool Calls ({stage.toolCallDetails.length})</span>
            <span className="text-xs text-gray-500">{showToolCalls ? 'Hide' : 'Show'}</span>
          </button>
          {showToolCalls && (
            <div className="mt-2 space-y-2">
              {stage.toolCallDetails.map((tc, i) => (
                <div key={i} className="rounded bg-gray-950/50 p-2 text-xs">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-indigo-200">{tc.tool}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                      tc.success ? 'bg-green-800 text-green-200' : 'bg-red-800 text-red-200'
                    }`}>
                      {tc.success ? 'OK' : 'FAIL'}
                    </span>
                    {tc.risk !== 'unknown' && (
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${
                        tc.risk === 'high' ? 'bg-red-900 text-red-300' :
                        tc.risk === 'medium' ? 'bg-yellow-900 text-yellow-300' :
                        'bg-gray-700 text-gray-300'
                      }`}>
                        {tc.risk}
                      </span>
                    )}
                    {tc.durationMs > 0 && (
                      <span className="text-gray-500">{tc.durationMs}ms</span>
                    )}
                    {tc.tokenTruncated && (
                      <span className="rounded bg-orange-900 px-1.5 py-0.5 text-[10px] text-orange-300">truncated</span>
                    )}
                    {tc.tokenBlocked && (
                      <span className="rounded bg-red-900 px-1.5 py-0.5 text-[10px] text-red-300">blocked</span>
                    )}
                  </div>
                  {tc.error && (
                    <div className="mt-1 text-red-300">{tc.error}</div>
                  )}
                  {Object.keys(tc.params).length > 0 && (
                    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap text-gray-400">
                      {JSON.stringify(tc.params, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
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

      {/* Agent Skills Popup */}
      {showSkillsPopup && roleInfo && stage.role && (
        <AgentSkillsPopup
          roleId={stage.role}
          role={roleInfo}
          onClose={() => setShowSkillsPopup(false)}
        />
      )}
    </div>
  )
}
