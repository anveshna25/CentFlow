import { useEffect, useState } from 'react'
import { authService } from '../../auth/authService'
import { useAuth } from '../../auth/AuthContext'
import '../../styles/auth.css'

export default function GoogleCallbackPage({ onComplete, onCancel }) {
  const { checkAuth } = useAuth()
  const [status, setStatus] = useState('processing') // 'processing' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState(null)

  useEffect(() => {
    let isMounted = true

    const processCallback = async () => {
      try {
        const params = new URLSearchParams(window.location.search)
        const code = params.get('code')
        const state = params.get('state')
        const error = params.get('error')

        if (error) {
          throw new Error(`Google Authentication error: ${error}`)
        }

        if (!code || !state) {
          throw new Error('Missing authorization code or state parameter in callback.')
        }

        const storedState = sessionStorage.getItem('oauth_state')
        const codeVerifier = sessionStorage.getItem('oauth_code_verifier')

        if (storedState && storedState !== state) {
          throw new Error('State parameter mismatch. Authentication request may have been forged.')
        }

        // Token exchange with backend
        await authService.handleGoogleCallback({
          code,
          state,
          code_verifier: codeVerifier || '',
        })

        // Clean up session storage
        sessionStorage.removeItem('oauth_state')
        sessionStorage.removeItem('oauth_code_verifier')

        // Refresh auth state in React context
        await checkAuth()

        if (isMounted) {
          setStatus('success')
          if (onComplete) {
            onComplete()
          } else {
            // Clean browser URL and navigate to home
            window.history.replaceState({}, document.title, '/')
            window.location.href = '/'
          }
        }
      } catch (err) {
        if (isMounted) {
          setStatus('error')
          setErrorMessage(err.message || 'Google authentication failed.')
          sessionStorage.removeItem('oauth_state')
          sessionStorage.removeItem('oauth_code_verifier')
        }
      }
    }

    processCallback()

    return () => {
      isMounted = false
    }
  }, [checkAuth, onComplete])

  return (
    <div className="auth-container">
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <div className="auth-brand" style={{ justifyContent: 'center' }}>
          <div className="auth-logo">CF</div>
          <span style={{ fontWeight: 700, fontSize: '1.25rem', color: '#f8fafc' }}>
            CentFlow
          </span>
        </div>

        {status === 'processing' && (
          <div style={{ padding: '32px 0' }}>
            <div className="auth-spinner" style={{ margin: '0 auto 20px' }}></div>
            <h2 className="auth-title" style={{ fontSize: '1.25rem' }}>
              Authenticating with Google...
            </h2>
            <p className="auth-subtitle">
              Verifying security credentials and establishing session
            </p>
          </div>
        )}

        {status === 'success' && (
          <div style={{ padding: '32px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>✅</div>
            <h2 className="auth-title" style={{ fontSize: '1.25rem' }}>
              Authentication Successful
            </h2>
            <p className="auth-subtitle">Redirecting to your dashboard...</p>
          </div>
        )}

        {status === 'error' && (
          <div style={{ padding: '24px 0' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>⚠️</div>
            <h2 className="auth-title" style={{ fontSize: '1.25rem' }}>
              Authentication Failed
            </h2>
            <div className="auth-error-box" style={{ margin: '16px 0', textAlign: 'left' }}>
              <span>⚠️</span>
              <span>{errorMessage}</span>
            </div>
            <button
              type="button"
              className="auth-btn-primary"
              onClick={onCancel || (() => { window.location.href = '/' })}
            >
              Return to Sign In
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
