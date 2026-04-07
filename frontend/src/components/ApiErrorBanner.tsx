/**
 * ApiErrorBanner — unified error display with Retry.
 * S79 FE-ERR-01: consistent error state across all pages.
 */

interface ApiErrorBannerProps {
  error: Error
  onRetry?: () => void
  compact?: boolean
}

export function ApiErrorBanner({ error, onRetry, compact }: ApiErrorBannerProps) {
  const isNetworkError =
    error.message.includes('fetch') ||
    error.message.includes('network') ||
    error.message.includes('Failed to fetch') ||
    error.message.includes('NetworkError')

  const displayMessage = isNetworkError
    ? 'API unreachable. The backend may be offline.'
    : error.message

  if (compact) {
    return (
      <div className="flex items-center gap-2 rounded border border-red-500/50 bg-red-950/30 px-3 py-2 text-sm text-red-300">
        <span>{displayMessage}</span>
        {onRetry && (
          <button
            onClick={onRetry}
            className="ml-auto shrink-0 rounded bg-red-800 px-2 py-0.5 text-xs font-medium text-red-100 hover:bg-red-700"
          >
            Retry
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="rounded border border-red-500/50 bg-red-950/30 p-4 text-red-300">
      <p className="font-medium">{isNetworkError ? 'API Unreachable' : 'Failed to load data'}</p>
      <p className="mt-1 text-sm">{displayMessage}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded bg-red-800 px-3 py-1.5 text-xs font-medium text-red-100 hover:bg-red-700"
        >
          Retry
        </button>
      )}
    </div>
  )
}
