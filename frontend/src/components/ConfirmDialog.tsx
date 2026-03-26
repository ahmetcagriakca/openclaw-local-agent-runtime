/**
 * ConfirmDialog — D-090: confirmation dialog for destructive actions.
 * Modal overlay with cancel/confirm buttons.
 * Destructive actions (cancel, reject) require explicit confirmation.
 */
interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'default'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null

  const confirmColor =
    variant === 'danger'
      ? 'bg-red-600 hover:bg-red-500 focus:ring-red-500'
      : 'bg-blue-600 hover:bg-blue-500 focus:ring-blue-500'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-modal="true" aria-labelledby="confirm-dialog-title" aria-describedby="confirm-dialog-desc">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60"
        onClick={loading ? undefined : onCancel}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-md rounded-lg border border-gray-700 bg-gray-800 p-6 shadow-xl">
        <h2 id="confirm-dialog-title" className="text-lg font-semibold text-gray-100">{title}</h2>
        <p id="confirm-dialog-desc" className="mt-2 text-sm text-gray-300">{message}</p>

        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="rounded px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`flex items-center gap-2 rounded px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50 ${confirmColor}`}
          >
            {loading && (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
