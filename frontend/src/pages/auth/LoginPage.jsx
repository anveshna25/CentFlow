import { useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { GoogleSignInButton } from '../../components/auth/GoogleSignInButton'
import '../../styles/auth.css'

export default function LoginPage({ onSwitchToRegister, onSwitchToForgot }) {
  const { login, error, clearError } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [localError, setLocalError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLocalError(null)
    clearError()

    if (!email.trim() || !password) {
      setLocalError('Please enter both your email address and password.')
      return
    }

    try {
      setIsSubmitting(true)
      await login(email.trim(), password)
    } catch (err) {
      setLocalError(err.message || 'Authentication failed. Please check your credentials.')
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
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">
            Sign in to access your quantitative market portfolio
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
            <label className="auth-label" htmlFor="login-email">
              Email Address
            </label>
            <input
              id="login-email"
              type="email"
              className="auth-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="trader@centflow.com"
              required
              autoFocus
            />
          </div>

          <div className="auth-field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="auth-label" htmlFor="login-password">
                Password
              </label>
              <button
                type="button"
                onClick={onSwitchToForgot}
                className="auth-link"
                style={{ fontSize: '0.75rem', background: 'none', border: 'none', padding: 0 }}
              >
                Forgot password?
              </button>
            </div>
            <input
              id="login-password"
              type="password"
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />
          </div>

          <button
            type="submit"
            className="auth-btn-primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Verifying Credentials...' : 'Sign In'}
          </button>
        </form>

        <div className="auth-divider">
          <span>or continue with</span>
        </div>

        <GoogleSignInButton disabled={isSubmitting} />

        <div className="auth-footer">
          Don't have an account?{' '}
          <button
            type="button"
            className="auth-link"
            onClick={onSwitchToRegister}
            style={{ background: 'none', border: 'none', padding: 0 }}
          >
            Create account
          </button>
        </div>
      </div>
    </div>
  )
}
