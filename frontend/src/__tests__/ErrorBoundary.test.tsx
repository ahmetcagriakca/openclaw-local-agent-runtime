/**
 * ErrorBoundary tests — error caught, retry works.
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorBoundary } from '../components/ErrorBoundary'

let shouldThrow = false

function ThrowingComponent() {
  if (shouldThrow) throw new Error('Test crash')
  return <div>Content OK</div>
}

describe('ErrorBoundary', () => {
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
    shouldThrow = false
  })
  afterEach(() => {
    console.error = originalError
  })

  it('renders children normally', () => {
    render(
      <ErrorBoundary>
        <div>All good</div>
      </ErrorBoundary>,
    )
    expect(screen.getByText('All good')).toBeInTheDocument()
  })

  it('catches error and shows fallback', () => {
    shouldThrow = true
    render(
      <ErrorBoundary fallbackLabel="Panel crashed">
        <ThrowingComponent />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Panel crashed')).toBeInTheDocument()
    expect(screen.getByText('Test crash')).toBeInTheDocument()
    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  it('retry resets the boundary', () => {
    shouldThrow = true
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>,
    )

    expect(screen.getByText('This panel encountered an error')).toBeInTheDocument()

    // Stop throwing before retry
    shouldThrow = false
    fireEvent.click(screen.getByText('Retry'))

    expect(screen.getByText('Content OK')).toBeInTheDocument()
  })
})
