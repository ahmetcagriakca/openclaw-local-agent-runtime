import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionStateBadge } from '../components/MissionStateBadge'

describe('MissionStateBadge', () => {
  test('renders state label with proper case', () => {
    render(<MissionStateBadge state="gate_check" />)
    expect(screen.getByText('Gate Check')).toBeTruthy()
  })

  test('renders completed state with green styling', () => {
    const { container } = render(<MissionStateBadge state="completed" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-green-600')
  })

  test('renders failed state with red styling', () => {
    const { container } = render(<MissionStateBadge state="failed" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-red-600')
  })

  test('renders unknown state with fallback gray and proper case', () => {
    const { container } = render(<MissionStateBadge state="unknown_state" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-gray-600')
    expect(screen.getByText('Unknown State')).toBeTruthy()
  })

  test('renders all known states without error', () => {
    const expected: Record<string, string> = {
      pending: 'Pending', planning: 'Planning', executing: 'Executing',
      gate_check: 'Gate Check', rework: 'Rework', approval_wait: 'Approval Wait',
      completed: 'Completed', failed: 'Failed', aborted: 'Aborted', timed_out: 'Timed Out',
    }
    for (const [state, label] of Object.entries(expected)) {
      const { unmount } = render(<MissionStateBadge state={state} />)
      expect(screen.getByText(label)).toBeTruthy()
      unmount()
    }
  })

  test('has tooltip with state description', () => {
    const { container } = render(<MissionStateBadge state="gate_check" />)
    const badge = container.querySelector('span')
    expect(badge?.getAttribute('title')).toContain('Quality gate')
  })

  test('includes running and paused states', () => {
    const { unmount: u1 } = render(<MissionStateBadge state="running" />)
    expect(screen.getByText('Running')).toBeTruthy()
    u1()

    const { container } = render(<MissionStateBadge state="paused" />)
    expect(screen.getByText('Paused')).toBeTruthy()
    expect(container.querySelector('span')?.className).toContain('bg-yellow-700')
  })
})
