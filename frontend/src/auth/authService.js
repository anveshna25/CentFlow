import { apiClient } from '../api/client'

const AUTH_BASE = '/api/v1/auth'

export const authService = {
  /**
   * Register a new user account with email/password.
   */
  async register(email, password, displayName) {
    const res = await apiClient(`${AUTH_BASE}/register`, {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    })
    return res.data
  },

  /**
   * Log in with email and password.
   */
  async login(email, password) {
    const res = await apiClient(`${AUTH_BASE}/login`, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    return res.data
  },

  /**
   * Revoke session and log out.
   */
  async logout() {
    const res = await apiClient(`${AUTH_BASE}/logout`, {
      method: 'POST',
    })
    return res.data
  },

  /**
   * Get current authenticated user profile.
   */
  async getMe() {
    const res = await apiClient(`${AUTH_BASE}/me`, {
      method: 'GET',
    })
    return res.data
  },

  /**
   * Get Google OAuth authorization URL and state.
   */
  async getGoogleAuthUrl() {
    const res = await apiClient(`${AUTH_BASE}/google/url`, {
      method: 'GET',
    })
    return res.data
  },

  /**
   * Complete Google OAuth callback code exchange.
   */
  async handleGoogleCallback(code, state, expectedState, codeVerifier) {
    const res = await apiClient(`${AUTH_BASE}/google/callback`, {
      method: 'POST',
      body: JSON.stringify({
        code,
        state,
        expected_state: expectedState,
        code_verifier: codeVerifier,
      }),
    })
    return res.data
  },

  /**
   * Verify email address with single-use token.
   */
  async verifyEmail(token) {
    const res = await apiClient(`${AUTH_BASE}/verify-email`, {
      method: 'POST',
      body: JSON.stringify({ token }),
    })
    return res.data
  },

  /**
   * Request password reset link/token.
   */
  async forgotPassword(email) {
    const res = await apiClient(`${AUTH_BASE}/forgot-password`, {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
    return res.data
  },

  /**
   * Complete password reset with new password.
   */
  async resetPassword(token, newPassword) {
    const res = await apiClient(`${AUTH_BASE}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    })
    return res.data
  },

  /**
   * Change password for currently authenticated user.
   */
  async changePassword(currentPassword, newPassword) {
    const res = await apiClient(`${AUTH_BASE}/change-password`, {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    })
    return res.data
  },

  /**
   * List all active sessions for current user.
   */
  async listSessions() {
    const res = await apiClient(`${AUTH_BASE}/sessions`, {
      method: 'GET',
    })
    return res.data
  },

  /**
   * Revoke a specific active session.
   */
  async revokeSession(sessionId) {
    const res = await apiClient(`${AUTH_BASE}/sessions/${sessionId}`, {
      method: 'DELETE',
    })
    return res.data
  },
}

