import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/client', () => ({
  getProviders: vi.fn(),
  getAgentRoles: vi.fn(),
  getCapabilityMatrix: vi.fn(),
  getAgentPerformance: vi.fn(),
}))

import { getProviders, getAgentRoles, getCapabilityMatrix, getAgentPerformance } from '../api/client'
import { AgentHealthPage } from '../pages/AgentHealthPage'

const mockProviders = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  status: 'partial',
  providers: [
    { name: 'OpenAI (GPT-4o)', provider: 'openai', model: 'gpt-4o', status: 'ok', detail: 'API key configured' },
    { name: 'Anthropic (Claude Sonnet)', provider: 'anthropic', model: 'claude-sonnet', status: 'ok', detail: 'API key configured' },
    { name: 'Ollama (Local)', provider: 'ollama', model: 'local', status: 'unavailable', detail: 'OLLAMA_URL not set' },
  ],
  available_count: 2,
  total_count: 3,
}

const mockRoles = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  total: 3,
  roles: [
    {
      id: 'developer', displayName: 'Developer', defaultSkill: 'controlled_execution',
      allowedSkills: ['controlled_execution'], forbiddenSkills: [], toolPolicy: 'full_24',
      allowedTools: ['read_file'], toolCount: 24, defaultModelTier: 2,
      preferredModel: 'gpt-4o', discoveryRights: 'secondary',
      maxFileReads: 50, maxDirectoryReads: 25, canExpand: true,
    },
    {
      id: 'analyst', displayName: 'Analyst', defaultSkill: 'repository_discovery',
      allowedSkills: ['repository_discovery'], forbiddenSkills: ['controlled_execution'],
      toolPolicy: 'read_only_13', allowedTools: ['read_file'], toolCount: 13,
      defaultModelTier: 2, preferredModel: 'claude-sonnet', discoveryRights: 'primary',
      maxFileReads: 30, maxDirectoryReads: 15, canExpand: true,
    },
    {
      id: 'product-owner', displayName: 'Product Owner', defaultSkill: 'requirement_structuring',
      allowedSkills: ['requirement_structuring'], forbiddenSkills: ['controlled_execution'],
      toolPolicy: 'no_tools', allowedTools: [], toolCount: 0,
      defaultModelTier: 2, preferredModel: 'gpt-4o', discoveryRights: 'forbidden',
      maxFileReads: 0, maxDirectoryReads: 0, canExpand: false,
    },
  ],
}

const mockMatrix = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  matrix: [
    { role: 'developer', displayName: 'Developer', preferredModel: 'gpt-4o', modelTier: 2, toolPolicy: 'full_24', toolCount: 24, canExpand: true, discoveryRights: 'secondary' },
    { role: 'analyst', displayName: 'Analyst', preferredModel: 'claude-sonnet', modelTier: 2, toolPolicy: 'read_only_13', toolCount: 13, canExpand: true, discoveryRights: 'primary' },
    { role: 'product-owner', displayName: 'Product Owner', preferredModel: 'gpt-4o', modelTier: 2, toolPolicy: 'no_tools', toolCount: 0, canExpand: false, discoveryRights: 'forbidden' },
  ],
}

const mockPerformance = {
  meta: { freshnessMs: 0, dataQuality: 'fresh', sourcesUsed: [], sourcesMissing: [], generatedAt: '' },
  performance: [
    { role: 'developer', missions: 5, stages: 10, tool_calls: 80, reworks: 1, avg_stage_duration_ms: 5000, rework_rate: 10.0 },
    { role: 'analyst', missions: 3, stages: 6, tool_calls: 30, reworks: 0, avg_stage_duration_ms: 3000, rework_rate: 0.0 },
  ],
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AgentHealthPage />
    </MemoryRouter>
  )
}

describe('AgentHealthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(getProviders as ReturnType<typeof vi.fn>).mockResolvedValue(mockProviders)
    ;(getAgentRoles as ReturnType<typeof vi.fn>).mockResolvedValue(mockRoles)
    ;(getCapabilityMatrix as ReturnType<typeof vi.fn>).mockResolvedValue(mockMatrix)
    ;(getAgentPerformance as ReturnType<typeof vi.fn>).mockResolvedValue(mockPerformance)
  })

  test('renders page title', async () => {
    renderPage()
    expect(screen.getByText('Agent Health')).toBeDefined()
  })

  test('shows provider status badge', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('2/3 Providers')).toBeDefined()
    })
  })

  test('shows provider cards', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('OpenAI (GPT-4o)')).toBeDefined()
    })
    expect(screen.getByText('Anthropic (Claude Sonnet)')).toBeDefined()
    expect(screen.getByText('Ollama (Local)')).toBeDefined()
  })

  test('shows provider status badges', async () => {
    renderPage()
    await waitFor(() => {
      const onlines = screen.getAllByText('Online')
      expect(onlines.length).toBe(2)
    })
    expect(screen.getByText('Unavailable')).toBeDefined()
  })

  test('shows capability matrix', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Role-Provider Capability Matrix')).toBeDefined()
    })
    expect(screen.getAllByText('Developer').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Analyst').length).toBeGreaterThan(0)
  })

  test('shows role cards', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Agent Roles/)).toBeDefined()
    })
  })

  test('shows role performance table', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Role Performance')).toBeDefined()
    })
  })

  test('calls all API functions on mount', async () => {
    renderPage()
    await waitFor(() => {
      expect(getProviders).toHaveBeenCalled()
    })
    expect(getAgentRoles).toHaveBeenCalled()
    expect(getCapabilityMatrix).toHaveBeenCalled()
    expect(getAgentPerformance).toHaveBeenCalled()
  })

  test('shows loading state', () => {
    ;(getProviders as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading providers...')).toBeDefined()
  })

  test('shows model info in provider cards', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Model: gpt-4o')).toBeDefined()
    })
    expect(screen.getByText('Model: claude-sonnet')).toBeDefined()
    expect(screen.getByText('Model: local')).toBeDefined()
  })
})
