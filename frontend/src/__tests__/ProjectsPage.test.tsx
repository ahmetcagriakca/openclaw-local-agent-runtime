import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../api/client', () => ({
  getProjects: vi.fn(),
}))

import { getProjects } from '../api/client'
import { ProjectsPage } from '../pages/ProjectsPage'

const mockMeta = { generatedAt: '2026-04-06T12:00:00Z', dataQuality: 'fresh' }

const mockResponse = {
  meta: mockMeta,
  data: [
    {
      project_id: 'proj_abc123',
      name: 'Test Project',
      description: 'A test project',
      status: 'active',
      owner: 'operator',
      created_at: '2026-04-06T10:00:00Z',
      updated_at: '2026-04-06T11:00:00Z',
    },
    {
      project_id: 'proj_def456',
      name: 'Archived Project',
      description: '',
      status: 'archived',
      owner: 'admin',
      created_at: '2026-04-01T10:00:00Z',
      updated_at: '2026-04-05T10:00:00Z',
    },
  ],
  total: 2,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ProjectsPage />
    </MemoryRouter>
  )
}

describe('ProjectsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(getProjects as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse)
  })

  test('renders page title with count', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Projects (2)')).toBeDefined()
    })
  })

  test('shows project names', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeDefined()
    })
    expect(screen.getByText('Archived Project')).toBeDefined()
  })

  test('shows project status badges', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('active')).toBeDefined()
    })
    expect(screen.getAllByText('archived').length).toBeGreaterThan(0)
  })

  test('shows project description', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('A test project')).toBeDefined()
    })
  })

  test('shows owner info', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Owner: operator')).toBeDefined()
    })
  })

  test('shows refresh button', () => {
    renderPage()
    expect(screen.getByText('Refresh')).toBeDefined()
  })

  test('shows loading state', () => {
    ;(getProjects as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading projects...')).toBeDefined()
  })

  test('shows error state with retry button', async () => {
    ;(getProjects as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeDefined()
    })
    expect(screen.getByText('Retry')).toBeDefined()
  })

  test('shows empty state', async () => {
    ;(getProjects as ReturnType<typeof vi.fn>).mockResolvedValue({
      meta: mockMeta, data: [], total: 0,
    })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('No projects found.')).toBeDefined()
    })
  })

  test('calls getProjects on mount', async () => {
    renderPage()
    await waitFor(() => {
      expect(getProjects).toHaveBeenCalled()
    })
  })

  test('has filter controls', () => {
    renderPage()
    expect(screen.getByPlaceholderText('Search projects...')).toBeDefined()
  })
})
