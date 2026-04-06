import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('../api/client', () => ({
  getProject: vi.fn(),
  getProjectRollup: vi.fn(),
  getProjectArtifacts: vi.fn(),
}))

import { getProject, getProjectRollup, getProjectArtifacts } from '../api/client'
import { ProjectDetailPage } from '../pages/ProjectDetailPage'

const mockMeta = { generatedAt: '2026-04-06T12:00:00Z', dataQuality: 'fresh' }

const mockProject = {
  meta: mockMeta,
  data: {
    project: {
      project_id: 'proj_abc123',
      name: 'Detail Test',
      description: 'A detailed project',
      status: 'active',
      owner: 'operator',
      created_at: '2026-04-06T10:00:00Z',
      updated_at: '2026-04-06T11:00:00Z',
    },
    mission_summary: {
      total: 3,
      by_status: { completed: 2, executing: 1 },
      active_count: 1,
      quiescent_count: 2,
      last_activity: '2026-04-06T11:00:00Z',
    },
  },
}

const mockRollup = {
  meta: mockMeta,
  data: {
    project_id: 'proj_abc123',
    total_missions: 3,
    by_status: { completed: 2, executing: 1 },
    active_count: 1,
    quiescent_count: 2,
    total_tokens: 1500,
    last_activity: '2026-04-06T11:00:00Z',
    computed_at: '2026-04-06T12:00:00Z',
  },
}

const mockArtifacts = {
  meta: mockMeta,
  data: [
    {
      artifact_id: 'art-1',
      mission_id: 'm1',
      source_path: '/src/art1.txt',
      published_path: '/proj/art1.txt',
      published_at: '2026-04-06T11:30:00Z',
    },
  ],
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/proj_abc123']}>
      <Routes>
        <Route path="/projects/:id" element={<ProjectDetailPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(getProject as ReturnType<typeof vi.fn>).mockResolvedValue(mockProject)
    ;(getProjectRollup as ReturnType<typeof vi.fn>).mockResolvedValue(mockRollup)
    ;(getProjectArtifacts as ReturnType<typeof vi.fn>).mockResolvedValue(mockArtifacts)
  })

  test('renders project name', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Detail Test')).toBeDefined()
    })
  })

  test('shows project status badge', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('active')).toBeDefined()
    })
  })

  test('shows project description', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('A detailed project')).toBeDefined()
    })
  })

  test('shows rollup KPIs', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Total Missions')).toBeDefined()
    })
    expect(screen.getByText('Active')).toBeDefined()
    expect(screen.getByText('Quiescent')).toBeDefined()
    expect(screen.getByText('Total Tokens')).toBeDefined()
  })

  test('shows missions by status breakdown', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Missions by Status')).toBeDefined()
    })
  })

  test('shows published artifacts', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Published Artifacts/)).toBeDefined()
    })
    expect(screen.getByText('art-1')).toBeDefined()
  })

  test('shows back link', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/All Projects/)).toBeDefined()
    })
  })

  test('shows loading state', () => {
    ;(getProject as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText('Loading project...')).toBeDefined()
  })

  test('shows error state', async () => {
    ;(getProject as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Not found'))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Error: Not found')).toBeDefined()
    })
  })

  test('calls all API endpoints', async () => {
    renderPage()
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith('proj_abc123')
    })
    expect(getProjectRollup).toHaveBeenCalledWith('proj_abc123')
    expect(getProjectArtifacts).toHaveBeenCalledWith('proj_abc123')
  })

  test('shows owner info', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/Owner: operator/)).toBeDefined()
    })
  })
})
