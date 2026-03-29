import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SessionManager } from '../components/SessionManager'

// Mock the AuthContext
const mockLogout = vi.fn()
const mockAuth = {
  isAuthenticated: true,
  userName: 'admin',
  apiKey: 'test-key',
  logout: mockLogout,
  login: vi.fn(),
  getAuthHeaders: vi.fn(),
}

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockAuth,
}))

describe('SessionManager', () => {
  test('renders not-authenticated state when not logged in', () => {
    mockAuth.isAuthenticated = false
    render(<SessionManager />)
    expect(screen.getByText('Not authenticated')).toBeTruthy()
    mockAuth.isAuthenticated = true
  })

  test('renders session info when authenticated', () => {
    render(<SessionManager />)
    expect(screen.getByText('Session')).toBeTruthy()
    expect(screen.getByText('admin')).toBeTruthy()
  })

  test('shows Active badge when session is not expired', () => {
    const future = new Date(Date.now() + 86400000).toISOString() // +1 day
    render(<SessionManager expiresAt={future} />)
    expect(screen.getByText('Active')).toBeTruthy()
  })

  test('shows Expired badge when session is expired', () => {
    const past = new Date(Date.now() - 86400000).toISOString() // -1 day
    render(<SessionManager expiresAt={past} />)
    // "Expired" appears twice: in the badge and in the expiry text
    const expired = screen.getAllByText('Expired')
    expect(expired.length).toBe(2)
  })

  test('shows Never for expiration when expiresAt is null', () => {
    render(<SessionManager expiresAt={null} />)
    expect(screen.getByText('Never')).toBeTruthy()
  })

  test('shows remaining days for future expiration', () => {
    const future = new Date(Date.now() + 3 * 86400000).toISOString() // +3 days
    const { container } = render(<SessionManager expiresAt={future} />)
    expect(container.textContent).toMatch(/\dd remaining/)
  })

  test('shows remaining hours for same-day expiration', () => {
    const future = new Date(Date.now() + 5 * 3600000).toISOString() // +5 hours
    const { container } = render(<SessionManager expiresAt={future} />)
    expect(container.textContent).toMatch(/\dh remaining/)
  })

  test('calls logout when Logout button clicked', () => {
    render(<SessionManager />)
    fireEvent.click(screen.getByText('Logout'))
    expect(mockLogout).toHaveBeenCalledOnce()
  })

  test('shows Unknown for userName when userName is null', () => {
    const originalName = mockAuth.userName
    mockAuth.userName = null as unknown as string
    render(<SessionManager />)
    expect(screen.getByText('Unknown')).toBeTruthy()
    mockAuth.userName = originalName
  })
})
