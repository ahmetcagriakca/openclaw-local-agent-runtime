import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DataQualityBadge } from '../components/DataQualityBadge'
import { DataQualityStatus } from '../types/api'

describe('DataQualityBadge — extended', () => {
  test('Fresh badge has green background', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Fresh} />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-green-600')
  })

  test('Degraded badge has red background', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Degraded} />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-red-600')
  })

  test('Stale badge has orange background', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Stale} />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-orange-500')
  })

  test('Unknown badge has gray background', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Unknown} />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-gray-500')
  })

  test('badge has icon aria-hidden for accessibility', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Fresh} />)
    const icon = container.querySelector('[aria-hidden="true"]')
    expect(icon).toBeTruthy()
  })

  test('tooltip contains only label when no detail or assessedAt', () => {
    const { container } = render(<DataQualityBadge quality={DataQualityStatus.Fresh} />)
    const badge = container.querySelector('span')
    expect(badge?.getAttribute('title')).toBe('Fresh')
  })

  test('handles unknown quality value gracefully', () => {
    // Cast to simulate an unknown enum value
    render(<DataQualityBadge quality={'bogus' as DataQualityStatus} />)
    // Should fall back to Unknown config
    expect(screen.getByText('Unknown')).toBeTruthy()
  })
})
