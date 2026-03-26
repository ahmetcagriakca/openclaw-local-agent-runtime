/**
 * AgentSkillsPopup — modal showing agent role details: skills, tools, model, prompt preview.
 */
import { useState } from 'react'
import type { RoleInfo } from '../types/api'

interface AgentSkillsPopupProps {
  roleId: string
  role: RoleInfo
  onClose: () => void
}

export function AgentSkillsPopup({ roleId, role, onClose }: AgentSkillsPopupProps) {
  const [expandPrompt, setExpandPrompt] = useState(false)

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="relative mx-4 max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-gray-600 bg-gray-800 p-6 shadow-2xl">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-3 top-3 rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
          aria-label="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>

        {/* Header */}
        <div className="mb-4">
          <h2 className="text-lg font-bold text-gray-100">{role.name}</h2>
          <span className="text-xs text-gray-400">{roleId}</span>
        </div>

        {/* Key info grid */}
        <div className="mb-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-xs text-gray-500">Default Skill</span>
            <p className="font-medium text-indigo-300">{role.defaultSkill || 'none'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Model</span>
            <p className="font-medium text-cyan-300">{role.model || 'default'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Tool Policy</span>
            <p className="font-medium text-gray-200">{role.toolPolicy || 'none'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Discovery Rights</span>
            <p className="font-medium text-gray-200">{role.discoveryRights || 'none'}</p>
          </div>
          <div>
            <span className="text-xs text-gray-500">Max File Reads</span>
            <p className="font-medium text-gray-200">{role.maxFileReads}</p>
          </div>
        </div>

        {/* Allowed Skills */}
        {role.allowedSkills.length > 0 && (
          <div className="mb-4">
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">Allowed Skills</h3>
            <div className="flex flex-wrap gap-2">
              {role.allowedSkills.map((skill) => (
                <span
                  key={skill}
                  className={`rounded-full px-3 py-1 text-xs font-medium ${
                    skill === role.defaultSkill
                      ? 'bg-indigo-800 text-indigo-200'
                      : 'bg-gray-700 text-gray-300'
                  }`}
                >
                  {skill}
                  {skill === role.defaultSkill && ' (default)'}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Tools */}
        <div className="mb-4">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
            Tools ({role.tools.length})
          </h3>
          {role.tools.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {role.tools.map((tool) => (
                <span
                  key={tool}
                  className="rounded bg-emerald-900/60 px-2 py-0.5 text-xs text-emerald-200"
                >
                  {tool}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-xs text-gray-500">No tools (prompt-only role)</span>
          )}
        </div>

        {/* Prompt Preview */}
        {role.promptPreview && (
          <div className="rounded border border-gray-600/50 bg-gray-900/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-400">System Prompt Preview</h3>
              <button
                onClick={() => setExpandPrompt(!expandPrompt)}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                {expandPrompt ? 'Collapse' : 'Expand'}
              </button>
            </div>
            <pre className={`whitespace-pre-wrap break-words text-xs leading-relaxed text-gray-300 ${
              expandPrompt ? '' : 'max-h-24 overflow-hidden'
            }`}>
              {role.promptPreview}
            </pre>
            {!expandPrompt && role.promptPreview.endsWith('...') && (
              <div className="mt-1 text-xs text-gray-500">... truncated</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
