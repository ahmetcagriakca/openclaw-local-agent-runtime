import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AgentSkillsPopup } from '../components/AgentSkillsPopup'
import type { RoleInfo } from '../types/api'

describe('AgentSkillsPopup', () => {
  const baseRole: RoleInfo = {
    name: 'Analyst',
    defaultSkill: 'analyze',
    allowedSkills: ['analyze', 'summarize'],
    toolPolicy: 'permissive',
    model: 'gpt-4o',
    tools: ['read_file', 'search'],
    discoveryRights: 'full',
    maxFileReads: 10,
    promptPreview: 'You are an analyst agent...',
  }

  test('renders role name and roleId', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('Analyst')).toBeTruthy()
    expect(screen.getByText('analyst')).toBeTruthy()
  })

  test('displays model and default skill', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('gpt-4o')).toBeTruthy()
    expect(screen.getByText('analyze')).toBeTruthy()
  })

  test('displays tool policy and discovery rights', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('permissive')).toBeTruthy()
    expect(screen.getByText('full')).toBeTruthy()
  })

  test('renders allowed skills with default marker', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('analyze (default)')).toBeTruthy()
    expect(screen.getByText('summarize')).toBeTruthy()
  })

  test('renders tools list with count', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('Tools (2)')).toBeTruthy()
    expect(screen.getByText('read_file')).toBeTruthy()
    expect(screen.getByText('search')).toBeTruthy()
  })

  test('shows "No tools" when tools array is empty', () => {
    const noToolsRole = { ...baseRole, tools: [] }
    render(<AgentSkillsPopup roleId="analyst" role={noToolsRole} onClose={vi.fn()} />)
    expect(screen.getByText('No tools (prompt-only role)')).toBeTruthy()
  })

  test('renders prompt preview section', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    expect(screen.getByText('System Prompt Preview')).toBeTruthy()
    expect(screen.getByText('You are an analyst agent...')).toBeTruthy()
  })

  test('expand/collapse prompt toggle works', () => {
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={vi.fn()} />)
    const expandBtn = screen.getByText('Expand')
    fireEvent.click(expandBtn)
    expect(screen.getByText('Collapse')).toBeTruthy()
  })

  test('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={onClose} />)
    const closeBtn = screen.getByLabelText('Close')
    fireEvent.click(closeBtn)
    expect(onClose).toHaveBeenCalledOnce()
  })

  test('calls onClose when clicking backdrop', () => {
    const onClose = vi.fn()
    const { container } = render(<AgentSkillsPopup roleId="analyst" role={baseRole} onClose={onClose} />)
    const backdrop = container.firstElementChild as HTMLElement
    fireEvent.click(backdrop)
    expect(onClose).toHaveBeenCalledOnce()
  })

  test('does not render allowed skills section when empty', () => {
    const role = { ...baseRole, allowedSkills: [] }
    render(<AgentSkillsPopup roleId="analyst" role={role} onClose={vi.fn()} />)
    expect(screen.queryByText('Allowed Skills')).toBeNull()
  })

  test('hides prompt preview when promptPreview is empty', () => {
    const role = { ...baseRole, promptPreview: '' }
    render(<AgentSkillsPopup roleId="analyst" role={role} onClose={vi.fn()} />)
    expect(screen.queryByText('System Prompt Preview')).toBeNull()
  })
})
