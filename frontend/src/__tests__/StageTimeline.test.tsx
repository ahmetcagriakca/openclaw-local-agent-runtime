import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { StageTimeline } from '../components/StageTimeline'
import type { StageDetail } from '../types/api'

const makeStage = (overrides: Partial<StageDetail> = {}): StageDetail => ({
  index: 0,
  role: 'analyst',
  status: 'completed',
  isRework: false,
  reworkCycle: 0,
  isRecovery: false,
  toolCalls: 3,
  policyDenies: 0,
  turnsUsed: 2,
  durationMs: 5000,
  startedAt: '2026-03-28T10:00:00Z',
  finishedAt: '2026-03-28T10:00:05Z',
  agentUsed: 'gpt-4o',
  result: null,
  error: null,
  gateResults: null,
  denyForensics: null,
  systemPrompt: null,
  userPrompt: null,
  toolCallDetails: [],
  ...overrides,
})

describe('StageTimeline', () => {
  test('shows empty message when no stages', () => {
    render(<StageTimeline stages={[]} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText('No stages yet')).toBeTruthy()
  })

  test('renders stage role names', () => {
    const stages = [
      makeStage({ index: 0, role: 'analyst' }),
      makeStage({ index: 1, role: 'developer' }),
    ]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText('analyst')).toBeTruthy()
    expect(screen.getByText('developer')).toBeTruthy()
  })

  test('renders stage status text', () => {
    const stages = [makeStage({ index: 0, status: 'completed' })]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText('completed')).toBeTruthy()
  })

  test('calls onSelect when stage button clicked', () => {
    const onSelect = vi.fn()
    const stages = [makeStage({ index: 0 }), makeStage({ index: 1, role: 'dev' })]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={onSelect} />)
    fireEvent.click(screen.getByText('dev'))
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  test('active stage has ring styling', () => {
    const stages = [makeStage({ index: 0 })]
    const { container } = render(
      <StageTimeline stages={stages} activeIndex={0} onSelect={vi.fn()} />,
    )
    const button = container.querySelector('button')
    expect(button?.className).toContain('ring-2')
  })

  test('non-active stage has no ring styling', () => {
    const stages = [makeStage({ index: 0 })]
    const { container } = render(
      <StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />,
    )
    const button = container.querySelector('button')
    expect(button?.className).not.toContain('ring-2')
  })

  test('shows gate passed indicator', () => {
    const stages = [
      makeStage({
        index: 0,
        gateResults: { gateName: 'g1', passed: true, findings: [] },
      }),
    ]
    const { container } = render(
      <StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />,
    )
    // Gate passed shows a checkmark
    const checkmarks = container.querySelectorAll('[title="Gate passed"]')
    expect(checkmarks.length).toBe(1)
  })

  test('shows gate failed indicator with finding count', () => {
    const stages = [
      makeStage({
        index: 0,
        gateResults: {
          gateName: 'g1',
          passed: false,
          findings: [
            { check: 'lint', status: 'fail', detail: 'error' },
            { check: 'test', status: 'fail', detail: 'error2' },
          ],
        },
      }),
    ]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText(/2/)).toBeTruthy()
  })

  test('shows rework indicator', () => {
    const stages = [makeStage({ index: 0, isRework: true, reworkCycle: 1 })]
    const { container } = render(
      <StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />,
    )
    const reworkIndicator = container.querySelector('[title="Rework cycle 1"]')
    expect(reworkIndicator).toBeTruthy()
  })

  test('shows agent model used', () => {
    const stages = [makeStage({ index: 0, agentUsed: 'claude-sonnet' })]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText('claude-sonnet')).toBeTruthy()
  })

  test('falls back to Stage N when role is empty', () => {
    const stages = [makeStage({ index: 5, role: '' })]
    render(<StageTimeline stages={stages} activeIndex={null} onSelect={vi.fn()} />)
    expect(screen.getByText('Stage 5')).toBeTruthy()
  })
})
