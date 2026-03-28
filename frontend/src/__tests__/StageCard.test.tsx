import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StageCard } from '../components/StageCard'
import type { StageDetail } from '../types/api'

// Mock the API client to avoid real HTTP calls
vi.mock('../api/client', () => ({
  getRoles: vi.fn().mockResolvedValue({ roles: {} }),
}))

describe('StageCard', () => {
  const baseStage: StageDetail = {
    index: 0,
    role: 'analyst',
    status: 'completed',
    isRework: false,
    reworkCycle: 0,
    isRecovery: false,
    toolCalls: 5,
    policyDenies: 0,
    turnsUsed: 3,
    durationMs: 12000,
    startedAt: '2026-03-28T10:00:00Z',
    finishedAt: '2026-03-28T10:00:12Z',
    agentUsed: 'gpt-4o',
    result: null,
    error: null,
    gateResults: null,
    denyForensics: null,
    systemPrompt: null,
    userPrompt: null,
    toolCallDetails: [],
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders stage role name', () => {
    render(<StageCard stage={baseStage} />)
    expect(screen.getByText('analyst')).toBeTruthy()
  })

  test('renders completed status with green badge', () => {
    render(<StageCard stage={baseStage} />)
    const statusBadge = screen.getByText('completed')
    expect(statusBadge.className).toContain('bg-green-800')
  })

  test('renders failed status with red badge', () => {
    render(<StageCard stage={{ ...baseStage, status: 'failed' }} />)
    const statusBadge = screen.getByText('failed')
    expect(statusBadge.className).toContain('bg-red-800')
  })

  test('shows rework badge when isRework', () => {
    render(<StageCard stage={{ ...baseStage, isRework: true, reworkCycle: 2 }} />)
    expect(screen.getByText('Rework #2')).toBeTruthy()
  })

  test('shows recovery badge', () => {
    render(<StageCard stage={{ ...baseStage, isRecovery: true }} />)
    expect(screen.getByText('Recovery')).toBeTruthy()
  })

  test('displays metrics', () => {
    render(<StageCard stage={baseStage} />)
    expect(screen.getByText('5')).toBeTruthy() // toolCalls
    expect(screen.getByText('0')).toBeTruthy() // policyDenies
    expect(screen.getByText('3')).toBeTruthy() // turnsUsed
  })

  test('shows error detail when error present', () => {
    render(<StageCard stage={{ ...baseStage, error: 'LLM timeout after 30s' }} />)
    expect(screen.getByText('Error Detail')).toBeTruthy()
    expect(screen.getByText('LLM timeout after 30s')).toBeTruthy()
  })

  test('shows agent model used', () => {
    render(<StageCard stage={baseStage} />)
    expect(screen.getByText('gpt-4o')).toBeTruthy()
  })
})
