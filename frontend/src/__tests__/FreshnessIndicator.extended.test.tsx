import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { FreshnessIndicator } from '../components/FreshnessIndicator'
import { DataQualityStatus } from '../types/api'

describe('FreshnessIndicator — extended', () => {
  const baseProps = {
    freshnessMs: 5000,
    sourcesUsed: [],
    sourcesMissing: [],
    lastFetchedAt: null,
  }

  test('shows milliseconds for very fresh data', () => {
    render(<FreshnessIndicator {...baseProps} freshnessMs={500} />)
    expect(screen.getByText('500ms ago')).toBeTruthy()
  })

  test('shows seconds for recent data', () => {
    render(<FreshnessIndicator {...baseProps} freshnessMs={30000} />)
    expect(screen.getByText('30s ago')).toBeTruthy()
  })

  test('shows minutes for older data', () => {
    render(<FreshnessIndicator {...baseProps} freshnessMs={180000} />)
    expect(screen.getByText('3m ago')).toBeTruthy()
  })

  test('shows hours for very old data', () => {
    render(<FreshnessIndicator {...baseProps} freshnessMs={7200000} />)
    expect(screen.getByText('2h ago')).toBeTruthy()
  })

  test('shows stale styling when over threshold', () => {
    const { container } = render(
      <FreshnessIndicator
        {...baseProps}
        freshnessMs={60000}
        staleThresholdMs={30000}
      />,
    )
    const wrapper = container.firstElementChild as HTMLElement
    expect(wrapper.className).toContain('border-red-500')
  })

  test('shows normal styling when under threshold', () => {
    const { container } = render(
      <FreshnessIndicator
        {...baseProps}
        freshnessMs={10000}
        staleThresholdMs={30000}
      />,
    )
    const wrapper = container.firstElementChild as HTMLElement
    expect(wrapper.className).not.toContain('border-red-500')
  })

  test('renders sources used', () => {
    render(
      <FreshnessIndicator
        {...baseProps}
        sourcesUsed={[
          { name: 'mission_store', ageMs: 1000, status: DataQualityStatus.Fresh },
          { name: 'trace_store', ageMs: 2000, status: DataQualityStatus.Fresh },
        ]}
      />,
    )
    expect(screen.getByText('mission_store, trace_store')).toBeTruthy()
  })

  test('renders sources missing', () => {
    render(
      <FreshnessIndicator
        {...baseProps}
        sourcesMissing={['metric_store', 'audit_store']}
      />,
    )
    expect(screen.getByText('Missing: metric_store, audit_store')).toBeTruthy()
  })

  test('does not render sources sections when empty', () => {
    const { container } = render(<FreshnessIndicator {...baseProps} />)
    expect(container.textContent).not.toContain('Missing:')
  })
})
