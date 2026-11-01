import { useAuth } from './AuthContext'

export function ProtectedRoute({ children, fallback = null }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '200px',
        }}
      >
        <div className="auth-spinner" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return fallback
  }

  return children
}
