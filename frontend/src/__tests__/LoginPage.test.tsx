import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from '../auth/LoginPage'

// Mock sessionStorage
const mockStorage: Record<string, string> = {}
vi.stubGlobal('sessionStorage', {
  getItem: (key: string) => mockStorage[key] ?? null,
  setItem: (key: string, value: string) => { mockStorage[key] = value },
  removeItem: (key: string) => { delete mockStorage[key] },
})

function renderLogin() {
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    Object.keys(mockStorage).forEach(k => delete mockStorage[k])
  })

  test('renders login form', () => {
    renderLogin()
    expect(screen.getByText('Vezir Platform')).toBeTruthy()
    expect(screen.getByLabelText('API Key')).toBeTruthy()
    expect(screen.getByText('Login')).toBeTruthy()
  })

  test('shows error for empty key', () => {
    renderLogin()
    fireEvent.click(screen.getByText('Login'))
    expect(screen.getByText('API key is required')).toBeTruthy()
  })

  test('shows error for invalid key format', () => {
    renderLogin()
    const input = screen.getByLabelText('API Key')
    fireEvent.change(input, { target: { value: 'invalid_key' } })
    fireEvent.click(screen.getByText('Login'))
    expect(screen.getByText(/Invalid key format/)).toBeTruthy()
  })

  test('accepts valid key format', () => {
    renderLogin()
    const input = screen.getByLabelText('API Key')
    fireEvent.change(input, { target: { value: 'vz_test_key_001' } })
    fireEvent.click(screen.getByText('Login'))
    // No error shown means accepted
    expect(screen.queryByText('API key is required')).toBeNull()
    expect(screen.queryByText(/Invalid key format/)).toBeNull()
  })

  test('stores key in sessionStorage on login', () => {
    renderLogin()
    const input = screen.getByLabelText('API Key')
    fireEvent.change(input, { target: { value: 'vz_test_key_001' } })
    fireEvent.click(screen.getByText('Login'))
    expect(mockStorage['vezir_auth']).toContain('vz_test_key_001')
  })

  test('has password type input for security', () => {
    renderLogin()
    const input = screen.getByLabelText('API Key')
    expect(input.getAttribute('type')).toBe('password')
  })

  test('shows admin contact message', () => {
    renderLogin()
    expect(screen.getByText(/Contact your administrator/)).toBeTruthy()
  })
})
