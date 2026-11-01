import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import { AuthProvider, useAuth } from '../AuthContext'
import { ProtectedRoute } from '../ProtectedRoute'
import { authService } from '../authService'

// Mock the authService
vi.mock('../authService', () => ({
  authService: {
    getMe: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  },
}))

function TestConsumer() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth()

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'loading' : 'ready'}</div>
      <div data-testid="auth-status">{isAuthenticated ? 'authenticated' : 'unauthenticated'}</div>
      <div data-testid="user-email">{user ? user.email : 'none'}</div>
      <button onClick={() => login('trader@centflow.com', 'SecurePass123!')}>Login</button>
      <button onClick={() => logout()}>Logout</button>
    </div>
  )
}

describe('AuthContext & Session Management', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes and verifies authenticated session when getMe succeeds', async () => {
    const mockUser = {
      id: 'usr-123',
      email: 'alex@centflow.com',
      display_name: 'Alex Morgan',
      is_active: true,
      has_password: true,
      identities: [],
    }
    authService.getMe.mockResolvedValueOnce(mockUser)

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')
    expect(screen.getByTestId('user-email').textContent).toBe('alex@centflow.com')
  })

  it('sets unauthenticated state when getMe fails with 401', async () => {
    authService.getMe.mockRejectedValueOnce(new Error('Unauthorized'))

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated')
    expect(screen.getByTestId('user-email').textContent).toBe('none')
  })

  it('logs in successfully and updates state', async () => {
    authService.getMe.mockRejectedValueOnce(new Error('Unauthorized'))
    authService.login.mockResolvedValueOnce({
      user: { id: 'usr-login', email: 'trader@centflow.com', display_name: 'Trader' },
      message: 'Login successful',
    })

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated')

    await act(async () => {
      screen.getByText('Login').click()
    })

    expect(authService.login).toHaveBeenCalledWith('trader@centflow.com', 'SecurePass123!')
    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')
    expect(screen.getByTestId('user-email').textContent).toBe('trader@centflow.com')
  })

  it('logs out successfully and resets state', async () => {
    const mockUser = { id: 'usr-logout', email: 'trader@centflow.com' }
    authService.getMe.mockResolvedValueOnce(mockUser)
    authService.logout.mockResolvedValueOnce({ message: 'Logged out' })

    await act(async () => {
      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('auth-status').textContent).toBe('authenticated')

    await act(async () => {
      screen.getByText('Logout').click()
    })

    expect(authService.logout).toHaveBeenCalled()
    expect(screen.getByTestId('auth-status').textContent).toBe('unauthenticated')
    expect(screen.getByTestId('user-email').textContent).toBe('none')
  })

  it('ProtectedRoute renders fallback when unauthenticated and children when authenticated', async () => {
    authService.getMe.mockRejectedValueOnce(new Error('Unauthorized'))
    authService.login.mockResolvedValueOnce({
      user: { id: 'usr-1', email: 'auth@centflow.com' },
      message: 'Login successful',
    })

    function ProtectedTestConsumer() {
      const { login } = useAuth()
      return (
        <div>
          <button onClick={() => login('auth@centflow.com', 'Pass123!')}>Do Login</button>
          <ProtectedRoute fallback={<div data-testid="fallback">Access Denied</div>}>
            <div data-testid="protected-content">Secret Trading Data</div>
          </ProtectedRoute>
        </div>
      )
    }

    await act(async () => {
      render(
        <AuthProvider>
          <ProtectedTestConsumer />
        </AuthProvider>
      )
    })

    expect(screen.getByTestId('fallback')).toBeDefined()
    expect(screen.queryByTestId('protected-content')).toBeNull()

    // Trigger login
    await act(async () => {
      screen.getByText('Do Login').click()
    })

    expect(screen.queryByTestId('fallback')).toBeNull()
    expect(screen.getByTestId('protected-content')).toBeDefined()
  })
})
