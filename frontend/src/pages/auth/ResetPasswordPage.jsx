import { useState } from 'react'
import { authService } from '../../auth/authService'
import '../../styles/auth.css'

export default function ResetPasswordPage({ onSwitchToLogin, initialToken = '' }) {
  const [token, setToken] = useState(() => {
    if (initialToken) return initialToken
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search)
      return params.get('token') || ''
    }
    return ''
  })
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!token.trim()) {
      setError('Please provide the recovery token sent to your email.')
      return
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match. Please verify.')
      return
    }

    try {
      setIsSubmitting(true)
      await authService.resetPassword(token.trim(), newPassword)
      setIsSuccess(true)
    } catch (err) {
      setError(err.message || 'Failed to reset password. The token may be expired or invalid.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-brand">
            <div className="auth-logo">CF</div>
            <span style={{ fontWeight: 700, fontSize: '1.25rem', color: '#f8fafc' }}>
              CentFlow
            </span>
          </div>
          <h1 className="auth-title">Set new password</h1>
          <p className="auth-subtitle">
            Create a secure password to regain account access
          </p>
        </div>

        {error && (
          <div className="auth-error-box" style={{ marginBottom: '18px' }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {isSuccess ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✅</div>
            <h3 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '8px' }}>
              Password Reset Complete
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', lineHeight: 1.5, marginBottom: '20px' }}>
              Your password has been successfully updated. You may now sign in with your new credentials.
            </p>
            <button
              type="button"
              className="auth-btn-primary"
              onClick={onSwitchToLogin}
            >
              Sign In Now
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="auth-field">
              <label className="auth-label" htmlFor="reset-token">
                Recovery Token
              </label>
              <input
                id="reset-token"
                type="text"
                className="auth-input"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="Paste your reset token"
                required
              />
            </div>

            <div className="auth-field">
              <label className="auth-label" htmlFor="reset-password">
                New Password
              </label>
              <input
                id="reset-password"
                type="password"
                className="auth-input"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
              />
            </div>

            <div className="auth-field">
              <label className="auth-label" htmlFor="reset-confirm">
                Confirm New Password
              </label>
              <input
                id="reset-confirm"
                type="password"
                className="auth-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                required
              />
            </div>

            <button
              type="submit"
              className="auth-btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Updating Password...' : 'Update Password'}
            </button>

            <div className="auth-footer" style={{ marginTop: '16px' }}>
              <button
                type="button"
                className="auth-link"
                onClick={onSwitchToLogin}
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                Back to Sign in
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
