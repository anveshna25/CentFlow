import { Header } from '../components/layout/Header'
import { Sidebar } from '../components/layout/Sidebar'

export function AppLayout({ children, onSearch, searchValue }) {
  return (
    <div
      id="cf-app-shell"
      style={{
        display: 'flex',
        minHeight: '100vh',
        background: 'var(--cf-bg-base)',
      }}
    >
      <Sidebar />
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minWidth: 0,
        }}
      >
        <Header onSearch={onSearch} searchValue={searchValue} />
        <main
          id="cf-main-content"
          style={{
            flex: 1,
            padding: 'var(--cf-space-6)',
            maxWidth: '1400px',
            width: '100%',
            margin: '0 auto',
          }}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
