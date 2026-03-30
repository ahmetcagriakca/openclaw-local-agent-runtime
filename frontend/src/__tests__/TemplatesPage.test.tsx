import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { MissionTemplate } from '../types/api'

// Mock API client — factory cannot reference outer variables (hoisted)
vi.mock('../api/client', () => ({
  getPresets: vi.fn(),
  getTemplates: vi.fn(),
  runTemplate: vi.fn(),
}))

import { getPresets } from '../api/client'
import { TemplatesPage } from '../pages/TemplatesPage'

const mockTemplates: MissionTemplate[] = [
  {
    id: 'tpl-001',
    name: 'Code Review',
    description: 'Automated code review for repositories.',
    version: '1.0.0',
    author: 'admin',
    status: 'published',
    parameters: [
      { name: 'repo_url', type: 'string', required: true, description: 'Repository URL' },
      { name: 'branch', type: 'string', required: false, description: 'Branch', default: 'main' },
    ],
    mission_config: {
      goal_template: 'Review {repo_url} on {branch}',
      specialist: 'analyst',
      provider: 'gpt-4o',
      max_stages: 5,
      timeout_minutes: 30,
    },
    created_at: '2026-03-29T10:00:00Z',
    updated_at: '2026-03-29T10:00:00Z',
  },
  {
    id: 'tpl-002',
    name: 'Security Scan',
    description: 'Run security scanning on a target.',
    version: '1.0.0',
    author: 'admin',
    status: 'published',
    parameters: [
      { name: 'target', type: 'string', required: true, description: 'Target URL' },
      { name: 'depth', type: 'number', required: false, description: 'Scan depth', default: 2 },
      { name: 'verbose', type: 'boolean', required: false, description: 'Verbose output', default: false },
    ],
    mission_config: {
      goal_template: 'Security scan {target} at depth {depth}',
      specialist: 'security',
      provider: 'gpt-4o',
      max_stages: 3,
      timeout_minutes: 20,
    },
    created_at: '2026-03-29T11:00:00Z',
    updated_at: '2026-03-29T11:00:00Z',
  },
]

function renderPage() {
  return render(
    <MemoryRouter>
      <TemplatesPage />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getPresets).mockResolvedValue(mockTemplates)
})

describe('TemplatesPage', () => {
  test('renders loading state initially', () => {
    vi.mocked(getPresets).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading templates...')).toBeTruthy()
  })

  test('renders template cards after fetch', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Code Review')).toBeTruthy()
    })
    expect(screen.getByText('Security Scan')).toBeTruthy()
  })

  test('shows template name and description', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Code Review')).toBeTruthy()
    })
    expect(screen.getByText('Automated code review for repositories.')).toBeTruthy()
    expect(screen.getByText('Run security scanning on a target.')).toBeTruthy()
  })

  test('shows parameter count on card', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Code Review')).toBeTruthy()
    })
    // Code Review has 2 params, Security Scan has 3 params
    expect(screen.getByText(/2 parameter/)).toBeTruthy()
    expect(screen.getByText(/3 parameter/)).toBeTruthy()
  })
})
