/**
 * ApiErrorBanner tests — S79 FE-ERR-01.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ApiErrorBanner } from '../components/ApiErrorBanner'

describe('ApiErrorBanner', () => {
  it('shows error message', () => {
    render(<ApiErrorBanner error={new Error('Something went wrong')} />)
    expect(screen.getByText('Something went wrong')).toBeDefined()
  })

  it('shows "API Unreachable" for network errors', () => {
    render(<ApiErrorBanner error={new Error('Failed to fetch')} />)
    expect(screen.getByText('API Unreachable')).toBeDefined()
    expect(screen.getByText(/API unreachable/)).toBeDefined()
  })

  it('shows Retry button when onRetry provided', () => {
    const onRetry = vi.fn()
    render(<ApiErrorBanner error={new Error('fail')} onRetry={onRetry} />)
    const btn = screen.getByText('Retry')
    expect(btn).toBeDefined()
    fireEvent.click(btn)
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('does not show Retry button without onRetry', () => {
    render(<ApiErrorBanner error={new Error('fail')} />)
    expect(screen.queryByText('Retry')).toBeNull()
  })

  it('renders compact variant', () => {
    render(<ApiErrorBanner error={new Error('fail')} compact />)
    expect(screen.getByText('fail')).toBeDefined()
  })

  it('shows "Failed to load data" for non-network errors', () => {
    render(<ApiErrorBanner error={new Error('Server error 500')} />)
    expect(screen.getByText('Failed to load data')).toBeDefined()
  })

  it('compact variant also shows Retry', () => {
    const onRetry = vi.fn()
    render(<ApiErrorBanner error={new Error('fail')} onRetry={onRetry} compact />)
    expect(screen.getByText('Retry')).toBeDefined()
  })
})
