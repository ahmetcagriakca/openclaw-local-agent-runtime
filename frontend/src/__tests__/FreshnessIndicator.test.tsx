import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import type { SourceInfo } from '../types/api'

describe('FreshnessIndicator', () => {
  const defaultProps = {
    freshnessMs: 5000,
    sourcesUsed: [{ name: 'state.json', freshness: 'fresh' }] as SourceInfo[],
    sourcesMissing: [] as string[],
    lastFetchedAt: null,
  }

  test('renders data age in seconds format', () => {
    render(<FreshnessIndicator {...defaultProps} freshnessMs={30000} />)
    expect(screen.getByText('30s ago')).toBeTruthy()
  })

  test('renders data age in minutes format', () => {
    render(<FreshnessIndicator {...defaultProps} freshnessMs={300000} />)
    expect(screen.getByText('5m ago')).toBeTruthy()
  })

  test('shows stale warning when threshold exceeded', () => {
    const { container } = render(
      <FreshnessIndicator {...defaultProps} freshnessMs={60000} staleThresholdMs={30000} />
    )
    expect(container.querySelector('.border-red-500\\/50')).toBeTruthy()
  })

  test('shows sources used', () => {
    render(<FreshnessIndicator {...defaultProps} />)
    expect(screen.getByText('state.json')).toBeTruthy()
  })

  test('shows missing sources', () => {
    render(
      <FreshnessIndicator {...defaultProps} sourcesMissing={['mission.json']} />
    )
    expect(screen.getByText(/Missing.*mission\.json/)).toBeTruthy()
  })
})
