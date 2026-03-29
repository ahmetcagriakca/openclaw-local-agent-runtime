import { describe, test, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorBoundary } from '../components/ErrorBoundary'

// Suppress console.error for expected error boundary triggers
const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('Test explosion')
  return <div>Child renders fine</div>
}

describe('ErrorBoundary — extended', () => {
  afterEach(() => {
    consoleSpy.mockClear()
  })

  test('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div>Healthy child</div>
      </ErrorBoundary>,
    )
    expect(screen.getByText('Healthy child')).toBeTruthy()
  })

  test('shows fallback when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('This panel encountered an error')).toBeTruthy()
    expect(screen.getByText('Test explosion')).toBeTruthy()
  })

  test('uses custom fallbackLabel', () => {
    render(
      <ErrorBoundary fallbackLabel="Mission panel crashed">
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Mission panel crashed')).toBeTruthy()
  })

  test('shows retry button', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Retry')).toBeTruthy()
  })

  test('retry button resets error state', () => {
    // Use a component that can toggle its throwing behavior
    let shouldThrow = true
    function ConditionalThrower() {
      if (shouldThrow) throw new Error('Boom')
      return <div>Recovered</div>
    }

    const { rerender } = render(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>,
    )

    expect(screen.getByText('This panel encountered an error')).toBeTruthy()

    // Stop throwing and click retry
    shouldThrow = false
    fireEvent.click(screen.getByText('Retry'))

    // After retry, the component should re-render its children
    rerender(
      <ErrorBoundary>
        <ConditionalThrower />
      </ErrorBoundary>,
    )
    expect(screen.getByText('Recovered')).toBeTruthy()
  })
})
