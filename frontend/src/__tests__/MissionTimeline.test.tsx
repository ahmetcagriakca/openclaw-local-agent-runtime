import { describe, test, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MissionTimeline } from '../components/MissionTimeline'
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

describe('MissionTimeline', () => {
  test('shows empty message when no stages', () => {
    render(<MissionTimeline stages={[]} missionId="mission-001" />)
    expect(screen.getByText('No stages recorded for mission-001')).toBeTruthy()
  })

  test('renders mission timeline header with mission ID', () => {
    render(<MissionTimeline stages={[makeStage()]} missionId="mission-001" />)
    expect(screen.getByText(/Mission Timeline — mission-001/)).toBeTruthy()
  })

  test('renders stage role name', () => {
    render(<MissionTimeline stages={[makeStage({ role: 'developer' })]} missionId="m-1" />)
    expect(screen.getByText('developer')).toBeTruthy()
  })

  test('renders stage status badges', () => {
    const stages = [
      makeStage({ index: 0, status: 'completed' }),
      makeStage({ index: 1, status: 'failed', role: 'tester' }),
    ]
    render(<MissionTimeline stages={stages} missionId="m-1" />)
    expect(screen.getByText('completed')).toBeTruthy()
    expect(screen.getByText('failed')).toBeTruthy()
  })

  test('shows duration in seconds', () => {
    render(<MissionTimeline stages={[makeStage({ durationMs: 12500 })]} missionId="m-1" />)
    expect(screen.getByText('12.5s')).toBeTruthy()
  })

  test('shows agent model used', () => {
    render(<MissionTimeline stages={[makeStage({ agentUsed: 'claude-sonnet' })]} missionId="m-1" />)
    expect(screen.getByText('claude-sonnet')).toBeTruthy()
  })

  test('shows error text when stage has error', () => {
    render(<MissionTimeline stages={[makeStage({ error: 'Token limit exceeded' })]} missionId="m-1" />)
    expect(screen.getByText('Token limit exceeded')).toBeTruthy()
  })

  test('renders multiple stages in order', () => {
    const stages = [
      makeStage({ index: 0, role: 'analyst' }),
      makeStage({ index: 1, role: 'developer' }),
      makeStage({ index: 2, role: 'tester' }),
    ]
    render(<MissionTimeline stages={stages} missionId="m-1" />)
    expect(screen.getByText('analyst')).toBeTruthy()
    expect(screen.getByText('developer')).toBeTruthy()
    expect(screen.getByText('tester')).toBeTruthy()
  })

  test('falls back to Stage N when role is empty', () => {
    render(<MissionTimeline stages={[makeStage({ role: '', index: 3 })]} missionId="m-1" />)
    expect(screen.getByText('Stage 3')).toBeTruthy()
  })
})
