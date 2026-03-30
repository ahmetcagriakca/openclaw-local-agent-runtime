import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/client', () => ({
  getCostSummary: vi.fn(),
  getCostMissions: vi.fn(),
  getCostTrends: vi.fn(),
}))

import { getCostSummary, getCostMissions, getCostTrends } from '../api/client'
import { CostDashboardPage } from '../pages/CostDashboardPage'

const mockSummary = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  total_missions: 10,
  completed: 8,
  failed: 2,
  success_rate: 80.0,
  total_tokens: 50000,
  total_estimated_cost: 2.75,
  avg_cost_per_mission: 0.275,
  avg_tokens_per_completed: 5000,
  avg_duration_ms: 15000,
  total_tool_calls: 120,
  total_reworks: 3,
  total_budget_events: 1,
  provider_breakdown: {
    'gpt-4o': { tokens: 30000, missions: 7, estimated_cost: 1.65 },
    'claude-sonnet': { tokens: 20000, missions: 3, estimated_cost: 1.10 },
  },
  pricing_model: {
    'gpt-4o': { input: 0.0025, output: 0.01 },
    'claude-sonnet': { input: 0.003, output: 0.015 },
  },
}

const mockMissions = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  total: 2,
  missions: [
    {
      id: 'mission-1', goal: 'Test mission', status: 'completed', complexity: 'medium',
      tokens: 5000, estimated_cost: 0.275, provider: 'gpt-4o', duration_ms: 10000,
      stages: 3, tool_calls: 15, reworks: 0, budget_pct: 10, ts: '2026-03-29T10:00:00Z',
    },
    {
      id: 'mission-2', goal: 'Failed mission', status: 'failed', complexity: 'high',
      tokens: 8000, estimated_cost: 0.44, provider: 'claude-sonnet', duration_ms: 20000,
      stages: 5, tool_calls: 25, reworks: 1, budget_pct: 16, ts: '2026-03-29T11:00:00Z',
    },
  ],
}

const mockTrends = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  bucket: 'daily',
  trends: [
    { period: '2026-03-29', tokens: 50000, estimated_cost: 2.75, missions: 10, completed: 8, failed: 2, success_rate: 80.0 },
  ],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <CostDashboardPage />
    </MemoryRouter>
  )
}

describe('CostDashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(getCostSummary as ReturnType<typeof vi.fn>).mockResolvedValue(mockSummary)
    ;(getCostMissions as ReturnType<typeof vi.fn>).mockResolvedValue(mockMissions)
    ;(getCostTrends as ReturnType<typeof vi.fn>).mockResolvedValue(mockTrends)
  })

  test('renders page title', async () => {
    renderPage()
    expect(screen.getByText('Cost & Outcomes')).toBeDefined()
  })

  test('shows KPI cards after loading', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Total Cost (Est.)')).toBeDefined()
    })
    expect(screen.getByText('Success Rate')).toBeDefined()
    expect(screen.getByText('Total Tokens')).toBeDefined()
    expect(screen.getByText('Avg Cost / Mission')).toBeDefined()
  })

  test('shows provider breakdown', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Provider Breakdown')).toBeDefined()
    })
    expect(screen.getAllByText('gpt-4o').length).toBeGreaterThan(0)
    expect(screen.getAllByText('claude-sonnet').length).toBeGreaterThan(0)
  })

  test('shows outcome metrics', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Outcome Metrics')).toBeDefined()
    })
    expect(screen.getByText('Avg Duration')).toBeDefined()
    expect(screen.getByText('Total Reworks')).toBeDefined()
    expect(screen.getByText('Budget Events')).toBeDefined()
  })

  test('shows cost trends section', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Cost Trends')).toBeDefined()
    })
    expect(screen.getByText('Daily')).toBeDefined()
    expect(screen.getByText('Weekly')).toBeDefined()
    expect(screen.getByText('Monthly')).toBeDefined()
  })

  test('shows per-mission cost table', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Per-Mission Costs/)).toBeDefined()
    })
    expect(screen.getByText('Test mission')).toBeDefined()
    expect(screen.getByText('Failed mission')).toBeDefined()
  })

  test('shows error state', async () => {
    ;(getCostSummary as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Failed to load cost data')).toBeDefined()
    })
  })

  test('shows loading state initially', () => {
    ;(getCostSummary as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading cost data...')).toBeDefined()
  })

  test('calls API functions on mount', async () => {
    renderPage()
    await waitFor(() => {
      expect(getCostSummary).toHaveBeenCalled()
    })
    expect(getCostMissions).toHaveBeenCalled()
    expect(getCostTrends).toHaveBeenCalled()
  })

  test('success rate color is green when >= 80', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getAllByText('80%').length).toBeGreaterThan(0)
    })
    const els = screen.getAllByText('80%')
    expect(els.some(el => el.className.includes('green'))).toBe(true)
  })
})
