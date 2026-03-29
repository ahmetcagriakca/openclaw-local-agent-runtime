import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Sidebar } from '../components/Sidebar'

function renderSidebar(props: Parameters<typeof Sidebar>[0] = {}) {
  return render(
    <MemoryRouter initialEntries={['/missions']}>
      <Sidebar {...props} />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  test('renders all navigation items in desktop mode', () => {
    renderSidebar({ collapsed: false })
    expect(screen.getByText('Missions')).toBeTruthy()
    expect(screen.getByText('Health')).toBeTruthy()
    expect(screen.getByText('Approvals')).toBeTruthy()
    expect(screen.getByText('Telemetry')).toBeTruthy()
    expect(screen.getByText('Monitoring')).toBeTruthy()
  })

  test('renders Vezir branding when expanded', () => {
    renderSidebar({ collapsed: false })
    expect(screen.getByText('Vezir')).toBeTruthy()
    expect(screen.getByText('Multi-Agent Platform')).toBeTruthy()
  })

  test('does not show labels when collapsed', () => {
    renderSidebar({ collapsed: true })
    // In collapsed mode, labels are hidden for nav items (only icons shown)
    // but the gear icon is shown instead of Vezir text
    expect(screen.queryByText('Multi-Agent Platform')).toBeNull()
  })

  test('calls onToggle when toggle button clicked', () => {
    const onToggle = vi.fn()
    renderSidebar({ collapsed: false, onToggle })
    // The toggle button is the last button in the sidebar
    const buttons = screen.getAllByRole('button')
    const toggleBtn = buttons[buttons.length - 1]!
    fireEvent.click(toggleBtn)
    expect(onToggle).toHaveBeenCalledOnce()
  })

  test('renders horizontal mode for mobile', () => {
    renderSidebar({ horizontal: true })
    const nav = screen.getByRole('navigation')
    expect(nav).toBeTruthy()
    expect(screen.getByText('Missions')).toBeTruthy()
    expect(screen.getByText('Health')).toBeTruthy()
  })

  test('calls onNavigate when link clicked in horizontal mode', () => {
    const onNavigate = vi.fn()
    renderSidebar({ horizontal: true, onNavigate })
    fireEvent.click(screen.getByText('Health'))
    expect(onNavigate).toHaveBeenCalledOnce()
  })

  test('has aria-label on navigation', () => {
    renderSidebar({ collapsed: false })
    const nav = screen.getByRole('navigation')
    expect(nav.getAttribute('aria-label')).toBe('Main navigation')
  })

  test('collapsed sidebar has narrow width class', () => {
    renderSidebar({ collapsed: true })
    const nav = screen.getByRole('navigation')
    expect(nav.className).toContain('w-14')
  })

  test('expanded sidebar has wider width class', () => {
    renderSidebar({ collapsed: false })
    const nav = screen.getByRole('navigation')
    expect(nav.className).toContain('w-52')
  })
})
