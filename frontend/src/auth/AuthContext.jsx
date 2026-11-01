import { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react'
import { setUnauthorizedHandler } from '../api/client'
import { authService } from './authService'

const DEFAULT_AUTH_CONTEXT = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  checkAuth: async () => {},
  clearError: () => {},
  setUser: () => {},
  setIsAuthenticated: () => {},
}

const AuthContext = createContext(DEFAULT_AUTH_CONTEXT)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)

  const clearError = useCallback(() => setError(null), [])

  const checkAuth = useCallback(async () => {
    try {
      setIsLoading(true)
      const userData = await authService.getMe()
      setUser(userData)
      setIsAuthenticated(true)
      setError(null)
      return userData
    } catch {
      setUser(null)
      setIsAuthenticated(false)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // Intercept 401s from any API request and cleanly transition to unauthenticated
    setUnauthorizedHandler(() => {
      setUser(null)
      setIsAuthenticated(false)
    })

    let isMounted = true

    authService
      .getMe()
      .then((userData) => {
        if (isMounted) {
          setUser(userData)
          setIsAuthenticated(true)
          setIsLoading(false)
        }
      })
      .catch(() => {
        if (isMounted) {
          setUser(null)
          setIsAuthenticated(false)
          setIsLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  const login = async (email, password) => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await authService.login(email, password)
      setUser(data.user)
      setIsAuthenticated(true)
      return data.user
    } catch (err) {
      setError(err.message || 'Login failed')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email, password, displayName) => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await authService.register(email, password, displayName)
      return data.user
    } catch (err) {
      setError(err.message || 'Registration failed')
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      setIsLoading(true)
      await authService.logout()
    } catch {
      // Ignored during client cleanup
    } finally {
      setUser(null)
      setIsAuthenticated(false)
      setIsLoading(false)
    }
  }

  const value = useMemo(
    () => ({
      user,
      isAuthenticated,
      isLoading,
      error,
      login,
      register,
      logout,
      checkAuth,
      clearError,
      setUser,
      setIsAuthenticated,
    }),
    [user, isAuthenticated, isLoading, error, checkAuth, clearError]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  return context || DEFAULT_AUTH_CONTEXT
}
