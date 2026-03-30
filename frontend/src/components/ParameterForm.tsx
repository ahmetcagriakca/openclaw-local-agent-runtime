/**
 * ParameterForm — B-104: dynamic form for template parameters.
 * Renders appropriate input fields based on parameter type.
 * Dark theme Tailwind styling matching project conventions.
 */
import type { TemplateParameter } from '../types/api'

interface ParameterFormProps {
  parameters: TemplateParameter[]
  values: Record<string, unknown>
  onChange: (values: Record<string, unknown>) => void
  errors?: Record<string, string>
}

export function ParameterForm({ parameters, values, onChange, errors }: ParameterFormProps) {
  const handleChange = (name: string, value: unknown) => {
    onChange({ ...values, [name]: value })
  }

  if (parameters.length === 0) {
    return <p className="text-sm text-gray-400">This template has no parameters.</p>
  }

  return (
    <div className="space-y-4">
      {parameters.map((param) => (
        <div key={param.name} className="space-y-1">
          <label htmlFor={`param-${param.name}`} className="block text-sm font-medium text-gray-200">
            {param.description || param.name}
            {param.required && <span className="ml-1 text-red-400">*</span>}
          </label>

          {param.type === 'boolean' ? (
            <label className="flex items-center gap-2 text-sm text-gray-300">
              <input
                id={`param-${param.name}`}
                type="checkbox"
                checked={Boolean(values[param.name] ?? param.default ?? false)}
                onChange={(e) => handleChange(param.name, e.target.checked)}
                className="h-4 w-4 rounded border-gray-600 bg-gray-700 text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
              />
              {param.name}
            </label>
          ) : param.type === 'number' ? (
            <input
              id={`param-${param.name}`}
              type="number"
              value={values[param.name] !== undefined ? String(values[param.name]) : (param.default !== undefined ? String(param.default) : '')}
              onChange={(e) => handleChange(param.name, e.target.value === '' ? '' : Number(e.target.value))}
              placeholder={param.default !== undefined ? String(param.default) : ''}
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          ) : (
            <input
              id={`param-${param.name}`}
              type="text"
              value={
                values[param.name] !== undefined
                  ? String(values[param.name])
                  : (param.default !== undefined
                    ? (Array.isArray(param.default) ? param.default.join(', ') : String(param.default))
                    : '')
              }
              onChange={(e) => handleChange(param.name, e.target.value)}
              placeholder={
                param.type === 'array'
                  ? 'Comma-separated values'
                  : (param.default !== undefined ? String(param.default) : '')
              }
              className="w-full rounded border border-gray-600 bg-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          )}

          {errors?.[param.name] && (
            <p className="text-xs text-red-400">{errors[param.name]}</p>
          )}
        </div>
      ))}
    </div>
  )
}
