/**
 * RunTemplateModal — B-104: modal dialog for running a mission template.
 * Shows template info, parameter form, goal preview, and run button.
 * Follows ConfirmDialog modal pattern with dark theme styling.
 */
import { useState, useEffect, useMemo } from 'react'
import type { MissionTemplate } from '../types/api'
import { runTemplate } from '../api/client'
import { ParameterForm } from './ParameterForm'

interface RunTemplateModalProps {
  template: MissionTemplate | null
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function RunTemplateModal({ template, open, onClose, onSuccess }: RunTemplateModalProps) {
  const [values, setValues] = useState<Record<string, unknown>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})

  // Reset state when template changes or modal opens
  useEffect(() => {
    if (open && template) {
      const defaults: Record<string, unknown> = {}
      for (const p of template.parameters) {
        if (p.default !== undefined) {
          defaults[p.name] = p.default
        }
      }
      setValues(defaults)
      setError(null)
      setSuccess(false)
      setValidationErrors({})
    }
  }, [open, template])

  // Check if all required params are filled
  const allRequiredFilled = useMemo(() => {
    if (!template) return false
    return template.parameters
      .filter((p) => p.required)
      .every((p) => {
        const v = values[p.name]
        if (v === undefined || v === '' || v === null) return false
        return true
      })
  }, [template, values])

  // Render goal preview by replacing {param} placeholders
  const goalPreview = useMemo(() => {
    if (!template) return ''
    let goal = template.mission_config.goal_template
    for (const [key, val] of Object.entries(values)) {
      if (val !== undefined && val !== '') {
        goal = goal.replace(new RegExp(`\\{${key}\\}`, 'g'), String(val))
      }
    }
    return goal
  }, [template, values])

  const handleRun = async () => {
    if (!template) return

    // Validate required fields
    const errs: Record<string, string> = {}
    for (const p of template.parameters) {
      if (p.required) {
        const v = values[p.name]
        if (v === undefined || v === '' || v === null) {
          errs[p.name] = 'This field is required'
        }
      }
    }
    if (Object.keys(errs).length > 0) {
      setValidationErrors(errs)
      return
    }

    setLoading(true)
    setError(null)
    setValidationErrors({})

    try {
      await runTemplate(template.id, values)
      setSuccess(true)
      setTimeout(() => {
        onClose()
        onSuccess?.()
      }, 1500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run template')
    } finally {
      setLoading(false)
    }
  }

  if (!open || !template) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="run-template-title">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={loading ? undefined : onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-xl">
        {/* Header */}
        <h2 id="run-template-title" className="text-lg font-semibold text-gray-100">
          {template.name}
        </h2>
        <p className="mt-1 text-sm text-gray-400">{template.description}</p>

        {/* Parameter Form */}
        {template.parameters.length > 0 && (
          <div className="mt-4">
            <h3 className="mb-2 text-sm font-medium text-gray-300">Parameters</h3>
            <ParameterForm
              parameters={template.parameters}
              values={values}
              onChange={setValues}
              errors={validationErrors}
            />
          </div>
        )}

        {/* Goal Preview */}
        <div className="mt-4">
          <h3 className="mb-1 text-sm font-medium text-gray-300">Goal Preview</h3>
          <div className="rounded border border-gray-600 bg-gray-900 p-3 text-sm text-gray-200">
            {goalPreview || <span className="text-gray-500">Fill in parameters to see goal...</span>}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 rounded border border-red-600/60 bg-red-950/40 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="mt-4 rounded border border-green-600/60 bg-green-950/40 p-3 text-sm text-green-300">
            Mission started successfully!
          </div>
        )}

        {/* Actions */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="rounded px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleRun}
            disabled={loading || !allRequiredFilled || success}
            className="flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50"
          >
            {loading && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            Run Mission
          </button>
        </div>
      </div>
    </div>
  )
}
