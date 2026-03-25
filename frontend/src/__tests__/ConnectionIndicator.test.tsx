/**
 * ConnectionIndicator tests — 4 states → 4 distinct visuals.
 */
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ConnectionIndicator } from '../components/ConnectionIndicator'

// Mock the SSEContext to control status
import * as SSEContextModule from '../hooks/SSEContext'
import { vi } from 'vitest'

import type { SSEStatus } from '../hooks/useSSE'

function renderWithStatus(status: SSEStatus, lastEventAt: Date | null = null) {
  vi.spyOn(SSEContextModule, 'useSSEContext').mockReturnValue({
    status,
    lastEventAt,
    subscribe: () => () => {},
  })
  return render(<ConnectionIndicator />)
}

describe('ConnectionIndicator', () => {
  it('shows "Live" when connected', () => {
    renderWithStatus('connected')
    expect(screen.getByText('Live')).toBeTruthy()
  })

  it('shows "Connecting…" when connecting', () => {
    renderWithStatus('connecting')
    expect(screen.getByText('Connecting…')).toBeTruthy()
  })

  it('shows "Reconnecting…" when reconnecting', () => {
    renderWithStatus('reconnecting')
    expect(screen.getByText('Reconnecting…')).toBeTruthy()
  })

  it('shows "Polling 30s" when polling', () => {
    renderWithStatus('polling')
    expect(screen.getByText('Polling 30s')).toBeTruthy()
  })

  it('has green dot for connected status', () => {
    const { container } = renderWithStatus('connected')
    const dot = container.querySelector('span.bg-green-500')
    expect(dot).toBeTruthy()
  })

  it('has pulse animation for connecting', () => {
    const { container } = renderWithStatus('connecting')
    const dot = container.querySelector('span.animate-pulse')
    expect(dot).toBeTruthy()
  })
})
