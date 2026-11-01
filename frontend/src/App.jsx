import { useState } from 'react'
import './App.css'
import { ThemeProvider } from './state/ThemeContext'
import { NavigationProvider, useNavigation } from './state/NavigationContext'
import { PAGES } from './state/pages'
import { AppLayout } from './layouts/AppLayout'
import { DashboardPage } from './pages/DashboardPage'
import { MarketsPage } from './pages/MarketsPage'
import { WatchlistsPage } from './pages/WatchlistsPage'
import { PortfoliosPage } from './pages/PortfoliosPage'
import { AssetDetailModal } from './components/market/AssetDetailModal'
import { AuthProvider, useAuth } from './auth/AuthContext'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ResetPasswordPage from './pages/auth/ResetPasswordPage'
import GoogleCallbackPage from './pages/auth/GoogleCallbackPage'

function MainContent({ searchValue }) {
  const { activePage } = useNavigation()

  switch (activePage) {
    case PAGES.MARKETS:
      return <MarketsPage externalSearch={searchValue} />
    case PAGES.WATCHLISTS:
      return <WatchlistsPage />
    case PAGES.PORTFOLIOS:
      return <PortfoliosPage />
    case PAGES.DASHBOARD:
    default:
      return <DashboardPage />
  }
}

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth()
  const [authView, setAuthView] = useState('login')
  const [searchValue, setSearchValue] = useState('')
  const [globalInspectingAsset, setGlobalInspectingAsset] = useState(null)

  // Check if current URL is OAuth callback
  const isGoogleCallback =
    typeof window !== 'undefined' &&
    (window.location.pathname.includes('/auth/google/callback') ||
      (window.location.search.includes('code=') && window.location.search.includes('state=')))

  if (isGoogleCallback) {
    return (
      <GoogleCallbackPage
        onComplete={() => {
          window.location.href = '/'
        }}
        onCancel={() => setAuthView('login')}
      />
    )
  }

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--cf-bg-base, #0b0f19)',
          gap: '16px',
        }}
      >
        <div className="auth-spinner" />
        <div style={{ color: 'var(--cf-text-secondary, #94a3b8)', fontSize: '14px', fontFamily: 'sans-serif' }}>
          Loading CentFlow...
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    switch (authView) {
      case 'register':
        return <RegisterPage onSwitchToLogin={() => setAuthView('login')} />
      case 'forgot':
        return (
          <ForgotPasswordPage
            onSwitchToLogin={() => setAuthView('login')}
            onSwitchToReset={() => setAuthView('reset')}
          />
        )
      case 'reset':
        return <ResetPasswordPage onSwitchToLogin={() => setAuthView('login')} />
      case 'login':
      default:
        return (
          <LoginPage
            onSwitchToRegister={() => setAuthView('register')}
            onSwitchToForgot={() => setAuthView('forgot')}
          />
        )
    }
  }

  return (
    <NavigationProvider>
      <AppLayout
        onSearch={setSearchValue}
        searchValue={searchValue}
        onSelectAsset={(asset) => setGlobalInspectingAsset(asset)}
      >
        <MainContent searchValue={searchValue} />
      </AppLayout>

      {globalInspectingAsset && (
        <AssetDetailModal
          instrument={globalInspectingAsset}
          onClose={() => setGlobalInspectingAsset(null)}
        />
      )}
    </NavigationProvider>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App
