import { useState } from 'react'
import { authService } from '../../auth/authService'
import '../../styles/auth.css'

export default function ForgotPasswordPage({ onSwitchToLogin, onSwitchToReset }) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)

    if (!email.trim()) {
      setError('Please enter your account email address.')
      return
    }

    try {
      setIsSubmitting(true)
      await authService.requestPasswordReset(email.trim())
      setSubmitted(true)
    } catch (err) {
      setError(err.message || 'Failed to submit recovery request.')
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
          <h1 className="auth-title">Reset your password</h1>
          <p className="auth-subtitle">
            Enter your verified email to receive a password recovery token
          </p>
        </div>

        {error && (
          <div className="auth-error-box" style={{ marginBottom: '18px' }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {submitted ? (
          <div style={{ textAlign: 'center', padding: '16px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✉️</div>
            <h3 style={{ color: '#f8fafc', fontSize: '1.1rem', marginBottom: '8px' }}>
              Recovery Instructions Sent
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem', lineHeight: 1.5, marginBottom: '20px' }}>
              If an account is associated with <strong>{email}</strong>, we have sent a secure recovery token.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                type="button"
                className="auth-btn-primary"
                onClick={onSwitchToReset}
              >
                I Have a Reset Token
              </button>
              <button
                type="button"
                className="auth-btn-google"
                onClick={onSwitchToLogin}
              >
                Back to Sign In
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            <div className="auth-field">
              <label className="auth-label" htmlFor="forgot-email">
                Email Address
              </label>
              <input
                id="forgot-email"
                type="email"
                className="auth-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="trader@centflow.com"
                required
                autoFocus
              />
            </div>

            <button
              type="submit"
              className="auth-btn-primary"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Sending Request...' : 'Send Recovery Token'}
            </button>

            <div className="auth-footer" style={{ marginTop: '16px' }}>
              Remember your password?{' '}
              <button
                type="button"
                className="auth-link"
                onClick={onSwitchToLogin}
                style={{ background: 'none', border: 'none', padding: 0 }}
              >
                Sign in
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
