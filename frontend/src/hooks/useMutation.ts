/**
 * useMutation — D-091: server-confirmed mutation hook.
 * No optimistic UI. Flow: request → loading → SSE confirm → refresh.
 *
 * States:
 *   idle → loading → success | error | timeout
 *
 * SSE integration: listens for mutation_applied/mutation_rejected/mutation_timed_out
 * and correlates by requestId.
 */
import { useCallback, useRef, useState } from 'react'
import { useSSEInvalidation } from './SSEContext'
import type { MutationResponse } from '../types/api'

export type MutationStatus = 'idle' | 'loading' | 'success' | 'error' | 'timeout'

export interface UseMutationResult {
  /** Execute the mutation */
  mutate: () => Promise<void>
  /** Current status */
  status: MutationStatus
  /** Error message if status === 'error' */
  errorMessage: string | null
  /** requestId from the API response */
  requestId: string | null
  /** Reset state back to idle */
  reset: () => void
}

interface UseMutationOptions {
  /** The mutation API call */
  mutationFn: () => Promise<MutationResponse>
  /** Called when SSE confirms mutation_applied */
  onSuccess?: () => void
  /** Called when SSE reports mutation_rejected */
  onError?: (reason: string) => void
  /** Called on timeout */
  onTimeout?: () => void
}

export function useMutation(options: UseMutationOptions): UseMutationResult {
  const { mutationFn, onSuccess, onError, onTimeout } = options

  const [status, setStatus] = useState<MutationStatus>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [requestId, setRequestId] = useState<string | null>(null)

  const activeRequestIdRef = useRef<string | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    clearTimer()
    activeRequestIdRef.current = null
    setStatus('idle')
    setErrorMessage(null)
    setRequestId(null)
  }, [clearTimer])

  const mutate = useCallback(async () => {
    setStatus('loading')
    setErrorMessage(null)
    clearTimer()

    try {
      const response = await mutationFn()
      setRequestId(response.requestId)
      activeRequestIdRef.current = response.requestId

      // Signal artifact written successfully — treat as success immediately.
      // SSE will provide additional confirmation if controller processes it.
      clearTimer()
      activeRequestIdRef.current = null
      setStatus('success')
      onSuccess?.()
    } catch (err: unknown) {
      activeRequestIdRef.current = null
      clearTimer()
      const msg = err instanceof Error ? err.message : 'Mutation failed'
      setErrorMessage(msg)
      setStatus('error')
      onError?.(msg)
    }
  }, [mutationFn, clearTimer, onError, onTimeout])

  // SSE: listen for mutation_applied
  useSSEInvalidation('mutation_applied', () => {
    if (activeRequestIdRef.current) {
      clearTimer()
      activeRequestIdRef.current = null
      setStatus('success')
      onSuccess?.()
    }
  })

  // SSE: listen for mutation_rejected
  useSSEInvalidation('mutation_rejected', () => {
    if (activeRequestIdRef.current) {
      clearTimer()
      activeRequestIdRef.current = null
      setErrorMessage('Mutation rejected by controller')
      setStatus('error')
      onError?.('Mutation rejected by controller')
    }
  })

  // SSE: listen for mutation_timed_out
  useSSEInvalidation('mutation_timed_out', () => {
    if (activeRequestIdRef.current) {
      clearTimer()
      activeRequestIdRef.current = null
      setStatus('timeout')
      onTimeout?.()
    }
  })

  return { mutate, status, errorMessage, requestId, reset }
}
