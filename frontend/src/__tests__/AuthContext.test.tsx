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

function TestComponent() {
  const { isAuthenticated, userName, login, logout, getAuthHeaders } = useAuth()
  return (
    <div>
      <span data-testid="status">{isAuthenticated ? 'authenticated' : 'anonymous'}</span>
      <span data-testid="user">{userName ?? 'none'}</span>
      <span data-testid="headers">{JSON.stringify(getAuthHeaders())}</span>
      <button onClick={() => login('vz_test_key', 'tester')}>Login</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach(k => delete mockStorage[k])
  })

  test('starts unauthenticated', () => {
    render(<AuthProvider><TestComponent /></AuthProvider>)
    expect(screen.getByTestId('status').textContent).toBe('anonymous')
    expect(screen.getByTestId('headers').textContent).toBe('{}')
  })

  test('login sets authenticated state', () => {
    render(<AuthProvider><TestComponent /></AuthProvider>)
    fireEvent.click(screen.getByText('Login'))
    expect(screen.getByTestId('status').textContent).toBe('authenticated')
    expect(screen.getByTestId('user').textContent).toBe('tester')
  })

  test('login provides auth headers', () => {
    render(<AuthProvider><TestComponent /></AuthProvider>)
    fireEvent.click(screen.getByText('Login'))
    expect(screen.getByTestId('headers').textContent).toContain('Bearer vz_test_key')
  })

  test('logout clears auth state', () => {
    render(<AuthProvider><TestComponent /></AuthProvider>)
    fireEvent.click(screen.getByText('Login'))
    fireEvent.click(screen.getByText('Logout'))
    expect(screen.getByTestId('status').textContent).toBe('anonymous')
    expect(screen.getByTestId('headers').textContent).toBe('{}')
  })

  test('persists to localStorage', () => {
    render(<AuthProvider><TestComponent /></AuthProvider>)
    fireEvent.click(screen.getByText('Login'))
    expect(mockStorage['vezir_auth']).toContain('vz_test_key')
  })
})
