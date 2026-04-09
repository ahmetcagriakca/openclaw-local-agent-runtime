import { describe, test, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SessionManager } from '../components/SessionManager'

// Mock the AuthContext — S84 unified auth state
const mockLogout = vi.fn()
const mockAuth = {
  isAuthenticated: true,
  user: {
    user_id: 'u1',
    username: 'admin',
    email: 'admin@vezir.dev',
    display_name: 'Admin User',
    role: 'operator',
    provider: 'apikey',
  },
  authMode: 'apikey' as 'none' | 'apikey' | 'oauth',
  accessToken: 'test-token',
  refreshToken: null,
  apiKey: 'test-key',
  userName: 'admin',
  logout: mockLogout,
  login: vi.fn(),
  loginWithOAuth: vi.fn(),
  getAuthHeaders: vi.fn(),
}

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockAuth,
}))

describe('SessionManager', () => {
  test('renders not-authenticated state when not logged in', () => {
    const originalAuth = mockAuth.isAuthenticated
    const originalUser = mockAuth.user
    mockAuth.isAuthenticated = false
    mockAuth.user = null as unknown as typeof mockAuth.user
    render(<SessionManager />)
    expect(screen.getByText('Not authenticated')).toBeTruthy()
    mockAuth.isAuthenticated = originalAuth
    mockAuth.user = originalUser
  })

  test('renders session info when authenticated', () => {
    render(<SessionManager />)
    expect(screen.getByText('Session')).toBeTruthy()
    expect(screen.getByText('Admin User')).toBeTruthy()
  })

  test('shows Active badge', () => {
    render(<SessionManager />)
    expect(screen.getByText('Active')).toBeTruthy()
  })

  test('shows role badge', () => {
    render(<SessionManager />)
    expect(screen.getByText('operator')).toBeTruthy()
  })

  test('shows auth mode for API key', () => {
    render(<SessionManager />)
    expect(screen.getByText('API Key')).toBeTruthy()
  })

  test('shows auth mode for OAuth', () => {
    const original = { ...mockAuth }
    mockAuth.authMode = 'oauth' as const
    mockAuth.user = { ...mockAuth.user, provider: 'github' }
    render(<SessionManager />)
    expect(screen.getByText('SSO (github)')).toBeTruthy()
    Object.assign(mockAuth, original)
  })

  test('shows email when available', () => {
    render(<SessionManager />)
    expect(screen.getByText('admin@vezir.dev')).toBeTruthy()
  })

  test('calls logout when Logout button clicked', () => {
    render(<SessionManager />)
    fireEvent.click(screen.getByText('Logout'))
    expect(mockLogout).toHaveBeenCalledOnce()
  })

  test('shows username when display_name is empty', () => {
    const original = mockAuth.user
    mockAuth.user = { ...mockAuth.user, display_name: '' }
    render(<SessionManager />)
    expect(screen.getByText('admin')).toBeTruthy()
    mockAuth.user = original
  })
})
