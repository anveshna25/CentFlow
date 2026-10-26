import { useNavigation } from '../../state/NavigationContext'
import { PAGES } from '../../state/pages'

export function Sidebar() {
  const { activePage, navigate } = useNavigation()

  const navItems = [
    {
      id: PAGES.DASHBOARD,
      label: 'Dashboard',
      icon: '📊',
      badge: null,
    },
    {
      id: PAGES.MARKETS,
      label: 'Markets & Assets',
      icon: '📈',
      badge: 'Live',
    },
    {
      id: PAGES.WATCHLISTS,
      label: 'Watchlists',
      icon: '⭐',
      badge: null,
    },
    {
      id: PAGES.PORTFOLIOS,
      label: 'Portfolios',
      icon: '💼',
      badge: null,
    },
  ]

  return (
    <aside
      id="cf-sidebar"
      style={{
        width: '240px',
        background: 'var(--cf-bg-sidebar)',
        borderRight: '1px solid var(--cf-border)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: 'var(--cf-space-5) var(--cf-space-3)',
        flexShrink: 0,
        height: '100vh',
        position: 'sticky',
        top: 0,
      }}
    >
      <div>
        {/* Brand Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--cf-space-3)',
            padding: '0 var(--cf-space-3) var(--cf-space-6)',
            borderBottom: '1px solid var(--cf-border)',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--cf-radius-md)',
              background: 'var(--cf-brand-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '16px',
              color: '#fff',
              boxShadow: 'var(--cf-brand-glow)',
            }}
          >
            CF
          </div>
          <div>
            <h2
              style={{
                fontSize: '17px',
                fontWeight: 700,
                margin: 0,
                letterSpacing: '-0.02em',
                color: 'var(--cf-text-primary)',
              }}
            >
              CentFlow
            </h2>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--cf-text-muted)',
                fontWeight: 500,
                display: 'block',
              }}
            >
              Market Intelligence
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav style={{ marginTop: 'var(--cf-space-5)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const isActive = activePage === item.id
            return (
              <button
                key={item.id}
                id={`cf-nav-${item.id}`}
                onClick={() => navigate(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  borderRadius: 'var(--cf-radius-md)',
                  background: isActive ? 'var(--cf-brand-subtle)' : 'transparent',
                  color: isActive ? 'var(--cf-text-primary)' : 'var(--cf-text-secondary)',
                  border: isActive ? '1px solid var(--cf-brand-border)' : '1px solid transparent',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: isActive ? 600 : 500,
                  transition: 'all var(--cf-transition-fast)',
                  textAlign: 'left',
                  width: '100%',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '15px' }}>{item.icon}</span>
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: 'var(--cf-radius-full)',
                      background: 'var(--cf-brand-subtle)',
                      color: 'var(--cf-brand-primary)',
                      border: '1px solid var(--cf-brand-border)',
                      fontWeight: 700,
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Footer Info */}
      <div
        style={{
          padding: 'var(--cf-space-3)',
          background: 'var(--cf-bg-surface-elevated)',
          borderRadius: 'var(--cf-radius-md)',
          border: '1px solid var(--cf-border)',
        }}
      >
        <span
          style={{
            fontSize: '11px',
            color: 'var(--cf-text-muted)',
            fontWeight: 600,
            textTransform: 'uppercase',
            display: 'block',
            marginBottom: '4px',
          }}
        >
          Platform Status
        </span>
        <span
          style={{
            fontSize: '12px',
            color: 'var(--cf-text-secondary)',
            fontWeight: 500,
            display: 'block',
          }}
        >
          Phase 7: Intelligence
        </span>
      </div>
    </aside>
  )
}
