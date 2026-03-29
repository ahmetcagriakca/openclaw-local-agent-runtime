import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuthProvider, useAuth } from '../auth/AuthContext'

const mockStorage: Record<string, string> = {}
vi.stubGlobal('sessionStorage', {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value },
  removeItem: (key: string) => { delete mockStorage[key] },
})

function HeaderDisplay() {
  const { getAuthHeaders, isAuthenticated, login, logout } = useAuth()
  const headers = getAuthHeaders()
  return (
    <div>
      <span data-testid="auth">{isAuthenticated ? 'yes' : 'no'}</span>
      <span data-testid="bearer">{headers.Authorization ?? 'none'}</span>
      <button onClick={() => login('vz_key1', 'user1')}>Login1</button>
      <button onClick={() => login('vz_key2', 'user2')}>Login2</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  )
}

describe('Auth Headers Integration', () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach(k => delete mockStorage[k])
  })

  test('no auth headers when unauthenticated', () => {
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    expect(screen.getByTestId('bearer').textContent).toBe('none')
  })

  test('bearer token in headers after login', () => {
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    fireEvent.click(screen.getByText('Login1'))
    expect(screen.getByTestId('bearer').textContent).toBe('Bearer vz_key1')
  })

  test('headers update on key change', () => {
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    fireEvent.click(screen.getByText('Login1'))
    expect(screen.getByTestId('bearer').textContent).toBe('Bearer vz_key1')
    fireEvent.click(screen.getByText('Login2'))
    expect(screen.getByTestId('bearer').textContent).toBe('Bearer vz_key2')
  })

  test('headers cleared on logout', () => {
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    fireEvent.click(screen.getByText('Login1'))
    fireEvent.click(screen.getByText('Logout'))
    expect(screen.getByTestId('bearer').textContent).toBe('none')
  })

  test('sessionStorage cleared on logout', () => {
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    fireEvent.click(screen.getByText('Login1'))
    expect(mockStorage['vezir_auth']).toBeDefined()
    fireEvent.click(screen.getByText('Logout'))
    expect(mockStorage['vezir_auth']).toBeUndefined()
  })

  test('restores from sessionStorage on mount', () => {
    mockStorage['vezir_auth'] = JSON.stringify({ apiKey: 'vz_stored', userName: 'stored-user' })
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    expect(screen.getByTestId('auth').textContent).toBe('yes')
    expect(screen.getByTestId('bearer').textContent).toBe('Bearer vz_stored')
  })

  test('handles corrupt sessionStorage gracefully', () => {
    mockStorage['vezir_auth'] = '{invalid json'
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    expect(screen.getByTestId('auth').textContent).toBe('no')
  })

  test('handles empty sessionStorage value', () => {
    mockStorage['vezir_auth'] = ''
    render(<AuthProvider><HeaderDisplay /></AuthProvider>)
    expect(screen.getByTestId('auth').textContent).toBe('no')
  })
})
