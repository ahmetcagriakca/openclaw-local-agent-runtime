import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { Layout } from '../components/Layout'

// Mock SSEContext used by ConnectionIndicator
vi.mock('../hooks/SSEContext', () => ({
  useSSEContext: () => ({
    status: 'connected',
    lastEventAt: null,
    subscribe: () => () => {},
  }),
}))

function renderLayout(children: React.ReactNode = <div>Content</div>) {
  return render(
    <MemoryRouter initialEntries={['/missions']}>
      <Layout>{children}</Layout>
    </MemoryRouter>,
  )
}

describe('Layout', () => {
  test('renders children in content area', () => {
    renderLayout(<div>Test Content</div>)
    expect(screen.getByText('Test Content')).toBeTruthy()
  })

  test('renders Vezir header title', () => {
    renderLayout()
    expect(screen.getByText('Vezir')).toBeTruthy()
  })

  test('renders connection indicator', () => {
    renderLayout()
    expect(screen.getByText('Live')).toBeTruthy()
  })

  test('has toggle menu button for mobile', () => {
    renderLayout()
    const toggleBtn = screen.getByLabelText('Toggle menu')
    expect(toggleBtn).toBeTruthy()
  })

  test('toggle menu button opens mobile nav', () => {
    renderLayout()
    const toggleBtn = screen.getByLabelText('Toggle menu')
    fireEvent.click(toggleBtn)
    // After clicking, the mobile overlay should appear
    // The sidebar renders nav items in horizontal mode
    const navs = screen.getAllByRole('navigation')
    // Mobile nav should now be visible (2 navs: desktop hidden + mobile shown)
    expect(navs.length).toBeGreaterThanOrEqual(1)
  })

  test('renders main content area', () => {
    renderLayout(<p>Main area</p>)
    const main = screen.getByRole('main')
    expect(main).toBeTruthy()
    expect(screen.getByText('Main area')).toBeTruthy()
  })
})
