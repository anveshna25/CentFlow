import { useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { GoogleSignInButton } from '../../components/auth/GoogleSignInButton'
import '../../styles/auth.css'

export default function RegisterPage({ onSwitchToLogin }) {
  const { register, error, clearError } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState(null)

  // Password validation checks
  const isLongEnough = password.length >= 8
  const hasDigitOrSpecial = /[\d!@#$%^&*(),.?":{}|<>]/.test(password)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLocalError(null)
    clearError()

    if (!displayName.trim()) {
      setLocalError('Please enter your full or display name.')
      return
    }

    if (!email.trim()) {
      setLocalError('Please enter a valid email address.')
      return
    }

    if (!isLongEnough) {
      setLocalError('Password must be at least 8 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match. Please re-enter them.')
      return
    }

    try {
      setIsSubmitting(true)
      await register(email.trim(), password, displayName.trim())
    } catch (err) {
      setLocalError(err.message || 'Registration failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const activeError = localError || error

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
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">
            Begin your data-driven portfolio management journey
          </p>
        </div>

        {activeError && (
          <div className="auth-error-box" style={{ marginBottom: '18px' }}>
            <span>⚠️</span>
            <span>{activeError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label className="auth-label" htmlFor="reg-name">
              Display Name
            </label>
            <input
              id="reg-name"
              type="text"
              className="auth-input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Alex Morgan"
              required
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="reg-email">
              Email Address
            </label>
            <input
              id="reg-email"
              type="email"
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="trader@centflow.com"
              required
            />
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="reg-password">
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
            />
            {password && (
              <div style={{ display: 'flex', gap: '12px', marginTop: '6px', fontSize: '0.75rem' }}>
                <span style={{ color: isLongEnough ? 'var(--color-primary-green)' : 'var(--color-text-muted)' }}>
                  {isLongEnough ? '✓' : '○'} 8+ chars
                </span>
                <span style={{ color: hasDigitOrSpecial ? 'var(--color-primary-green)' : 'var(--color-text-muted)' }}>
                  {hasDigitOrSpecial ? '✓' : '○'} Number or symbol
                </span>
              </div>
            )}
          </div>

          <div className="auth-field">
            <label className="auth-label" htmlFor="reg-confirm">
              Confirm Password
            </label>
            <input
              id="reg-confirm"
              type="password"
              className="auth-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter password"
              required
            />
          </div>

          <button
            type="submit"
            className="auth-btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Creating Account...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-divider">
          <span>or sign up with</span>
        </div>

        <GoogleSignInButton disabled={isSubmitting} />

        <div className="auth-footer">
          Already have an account?{' '}
          <button
            type="button"
            className="auth-link"
            onClick={onSwitchToLogin}
            style={{ background: 'none', border: 'none', padding: 0 }}
          >
            Sign in
          </button>
        </div>
      </div>
    </div>
  )
}
