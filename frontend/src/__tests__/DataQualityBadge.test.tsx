/**
 * DataQualityBadge tests — 6 distinct states render.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { DataQualityStatus } from '../types/api'

describe('DataQualityBadge', () => {
  const states: { status: DataQualityStatus; label: string }[] = [
    { status: DataQualityStatus.Fresh, label: 'Fresh' },
    { status: DataQualityStatus.Partial, label: 'Partial' },
    { status: DataQualityStatus.Stale, label: 'Stale' },
    { status: DataQualityStatus.Degraded, label: 'Degraded' },
    { status: DataQualityStatus.Unknown, label: 'Unknown' },
    { status: DataQualityStatus.NotReached, label: 'Not Reached' },
  ]

  states.forEach(({ status, label }) => {
    it(`renders ${label} state`, () => {
      render(<DataQualityBadge quality={status} />)
      expect(screen.getByText(label)).toBeInTheDocument()
    })
  })

  it('renders 6 distinct states', () => {
    expect(Object.values(DataQualityStatus)).toHaveLength(6)
  })

  it('shows tooltip with detail', () => {
    render(
      <DataQualityBadge
        quality={DataQualityStatus.Stale}
        detail="2 sources stale"
        assessedAt="2026-03-25T10:00:00Z"
      />,
    )
    const badge = screen.getByText('Stale').closest('span')
    expect(badge?.getAttribute('title')).toContain('2 sources stale')
    expect(badge?.getAttribute('title')).toContain('2026-03-25T10:00:00Z')
  })
})
