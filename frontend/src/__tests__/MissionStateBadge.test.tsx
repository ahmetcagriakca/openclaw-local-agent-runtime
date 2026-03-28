import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionStateBadge } from '../components/MissionStateBadge'

describe('MissionStateBadge', () => {
  test('renders state label with underscores replaced by spaces', () => {
    render(<MissionStateBadge state="gate_check" />)
    expect(screen.getByText('gate check')).toBeTruthy()
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

  test('renders unknown state with fallback gray', () => {
    const { container } = render(<MissionStateBadge state="unknown_state" />)
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('bg-gray-600')
    expect(screen.getByText('unknown state')).toBeTruthy()
  })

  test('renders all known states without error', () => {
    const states = ['pending', 'planning', 'executing', 'gate_check', 'rework',
                    'approval_wait', 'completed', 'failed', 'aborted', 'timed_out']
    for (const state of states) {
      const { unmount } = render(<MissionStateBadge state={state} />)
      expect(screen.getByText(state.replace(/_/g, ' '))).toBeTruthy()
      unmount()
    }
  })
})
