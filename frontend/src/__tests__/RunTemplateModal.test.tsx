import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { RunTemplateModal } from '../components/RunTemplateModal'
import type { MissionTemplate } from '../types/api'

// Mock API client
vi.mock('../api/client', () => ({
  runTemplate: vi.fn().mockResolvedValue({ requestId: 'req-1' }),
}))

const template: MissionTemplate = {
  id: 'tpl-001',
  name: 'Code Review',
  description: 'Run an automated code review on a repository.',
  version: '1.0.0',
  author: 'admin',
  status: 'published',
  parameters: [
    {
      name: 'repo_url',
      type: 'string',
      required: true,
      description: 'Repository URL',
    },
    {
      name: 'branch',
      type: 'string',
      required: false,
      description: 'Branch name',
      default: 'main',
    },
    {
      name: 'depth',
      type: 'number',
      required: false,
      description: 'Review depth',
      default: 3,
    },
  ],
  mission_config: {
    goal_template: 'Review code in {repo_url} on branch {branch} with depth {depth}',
    specialist: 'analyst',
    provider: 'gpt-4o',
    max_stages: 5,
    timeout_minutes: 30,
  },
  created_at: '2026-03-29T10:00:00Z',
  updated_at: '2026-03-29T10:00:00Z',
}

describe('RunTemplateModal', () => {
  test('renders nothing when closed', () => {
    const { container } = render(
      <RunTemplateModal template={template} open={false} onClose={vi.fn()} />,
    )
    expect(container.innerHTML).toBe('')
  })

  test('renders nothing when template is null', () => {
    const { container } = render(
      <RunTemplateModal template={null} open={true} onClose={vi.fn()} />,
    )
    expect(container.innerHTML).toBe('')
  })

  test('renders template name and description', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Code Review')).toBeTruthy()
    expect(screen.getByText('Run an automated code review on a repository.')).toBeTruthy()
  })

  test('shows parameter form with inputs', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    expect(screen.getByLabelText(/Repository URL/i)).toBeTruthy()
    expect(screen.getByLabelText(/Branch name/i)).toBeTruthy()
    expect(screen.getByLabelText(/Review depth/i)).toBeTruthy()
  })

  test('disables run button when required params missing', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    const runBtn = screen.getByText('Run Mission')
    expect(runBtn.hasAttribute('disabled')).toBe(true)
  })

  test('shows goal preview with parameter substitution', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    // Default values should be substituted: branch=main, depth=3
    // repo_url has no default so it stays as {repo_url}
    expect(screen.getByText(/branch main/)).toBeTruthy()
    expect(screen.getByText(/depth 3/)).toBeTruthy()
  })

  test('shows Parameters heading', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Parameters')).toBeTruthy()
  })

  test('shows Goal Preview heading', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Goal Preview')).toBeTruthy()
  })

  test('has cancel button', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  test('has aria attributes for accessibility', () => {
    render(<RunTemplateModal template={template} open={true} onClose={vi.fn()} />)
    const dialog = screen.getByRole('dialog')
    expect(dialog.getAttribute('aria-modal')).toBe('true')
  })
})
