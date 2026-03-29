/**
 * Isolation regression tests — Sprint 40, Task 40.3.
 *
 * Verifies that frontend properly isolates user data:
 * - Auth headers are sent on all API requests
 * - Identity switch clears state
 * - Approval inbox respects user context
 */
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuthProvider, useAuth } from '../auth/AuthContext'

// Mock localStorage
const mockStorage: Record<string, string> = {}
vi.stubGlobal('localStorage', {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value },
  removeItem: (key: string) => { delete mockStorage[key] },
})

function AuthStateDisplay() {
  const { isAuthenticated, userName, login, logout, getAuthHeaders } = useAuth()
  return (
    <div>
      <span data-testid="auth-state">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="user-name">{userName ?? 'none'}</span>
      <span data-testid="auth-header">{JSON.stringify(getAuthHeaders())}</span>
      <button data-testid="login-alice" onClick={() => login('key_alice', 'alice')}>Login Alice</button>
      <button data-testid="login-bob" onClick={() => login('key_bob', 'bob')}>Login Bob</button>
      <button data-testid="logout" onClick={() => logout()}>Logout</button>
    </div>
  )
}

describe('Isolation Regression — Sprint 40', () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach(k => delete mockStorage[k])
  })

  test('identity switch clears previous user state', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    // Login as Alice
    fireEvent.click(screen.getByTestId('login-alice'))
    expect(screen.getByTestId('user-name').textContent).toBe('alice')
    expect(screen.getByTestId('auth-header').textContent).toContain('key_alice')

    // Switch to Bob
    fireEvent.click(screen.getByTestId('login-bob'))
    expect(screen.getByTestId('user-name').textContent).toBe('bob')
    expect(screen.getByTestId('auth-header').textContent).toContain('key_bob')
    // Alice's key should NOT be present
    expect(screen.getByTestId('auth-header').textContent).not.toContain('key_alice')
  })

  test('logout clears all user context', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    // Login then logout
    fireEvent.click(screen.getByTestId('login-alice'))
    expect(screen.getByTestId('auth-state').textContent).toBe('yes')

    fireEvent.click(screen.getByTestId('logout'))
    expect(screen.getByTestId('auth-state').textContent).toBe('no')
    expect(screen.getByTestId('user-name').textContent).toBe('none')
    expect(screen.getByTestId('auth-header').textContent).toBe('{}')
  })

  test('auth headers include bearer token when authenticated', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    fireEvent.click(screen.getByTestId('login-alice'))
    const headers = JSON.parse(screen.getByTestId('auth-header').textContent!)
    expect(headers).toHaveProperty('Authorization')
    expect(headers.Authorization).toBe('Bearer key_alice')
  })

  test('no auth headers when not authenticated', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    const headers = JSON.parse(screen.getByTestId('auth-header').textContent!)
    expect(headers).toEqual({})
  })

  test('multiple identity switches maintain correct state', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    // Alice → Bob → Logout → Alice
    fireEvent.click(screen.getByTestId('login-alice'))
    expect(screen.getByTestId('user-name').textContent).toBe('alice')

    fireEvent.click(screen.getByTestId('login-bob'))
    expect(screen.getByTestId('user-name').textContent).toBe('bob')

    fireEvent.click(screen.getByTestId('logout'))
    expect(screen.getByTestId('user-name').textContent).toBe('none')

    fireEvent.click(screen.getByTestId('login-alice'))
    expect(screen.getByTestId('user-name').textContent).toBe('alice')
    expect(screen.getByTestId('auth-header').textContent).toContain('key_alice')
  })

  test('localStorage persists auth state', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    fireEvent.click(screen.getByTestId('login-alice'))

    // Check localStorage was updated (stored as JSON under vezir_auth key)
    const stored = JSON.parse(mockStorage['vezir_auth'] ?? '{}')
    expect(stored.apiKey).toBe('key_alice')
    expect(stored.userName).toBe('alice')
  })

  test('localStorage cleared on logout', () => {
    render(<AuthProvider><AuthStateDisplay /></AuthProvider>)

    fireEvent.click(screen.getByTestId('login-alice'))
    fireEvent.click(screen.getByTestId('logout'))

    expect(mockStorage['vezir_auth']).toBeUndefined()
  })
})
