import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionStateBadge } from '../components/MissionStateBadge'

describe('MissionStateBadge — extended', () => {
  test('renders executing state with indigo styling', () => {
    const { container } = render(<MissionStateBadge state="executing" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-indigo-600')
  })

  test('renders pending state with gray styling', () => {
    const { container } = render(<MissionStateBadge state="pending" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-gray-600')
  })

  test('renders aborted state with red styling', () => {
    const { container } = render(<MissionStateBadge state="aborted" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-red-800')
  })

  test('renders timed_out state label correctly', () => {
    render(<MissionStateBadge state="timed_out" />)
    expect(screen.getByText('timed out')).toBeTruthy()
  })

  test('renders approval_wait state label correctly', () => {
    render(<MissionStateBadge state="approval_wait" />)
    expect(screen.getByText('approval wait')).toBeTruthy()
  })

  test('badge is an inline element (span)', () => {
    const { container } = render(<MissionStateBadge state="completed" />)
    const badge = container.querySelector('span')
    expect(badge?.tagName).toBe('SPAN')
  })
})
