import { StatWidget } from '../components/market/StatWidget'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { useNavigation } from '../state/NavigationContext'
import { PAGES } from '../state/pages'

const FEATURED_ASSETS = [
  { symbol: 'AAPL', name: 'Apple Inc.', type: 'equity', price: '$185.50', change: '+0.87%', isUp: true, exchange: 'NASDAQ' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', type: 'equity', price: '$420.25', change: '+0.83%', isUp: true, exchange: 'NASDAQ' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', type: 'crypto', price: '$65,400.00', change: '+1.95%', isUp: true, exchange: 'Coinbase' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', type: 'crypto', price: '$3,450.00', change: '+1.77%', isUp: true, exchange: 'Coinbase' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF', type: 'etf', price: '$510.15', change: '+0.50%', isUp: true, exchange: 'NYSE' },
]

export function DashboardPage() {
  const { navigate } = useNavigation()

  return (
    <div id="cf-dashboard-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Welcome Banner */}
      <section
        style={{
          background: 'radial-gradient(100% 100% at 0% 0%, rgba(59, 130, 246, 0.15) 0%, rgba(139, 92, 246, 0.05) 50%, transparent 100%), var(--cf-bg-surface-glass)',
          border: '1px solid var(--cf-border)',
          borderRadius: 'var(--cf-radius-xl)',
          padding: 'var(--cf-space-6)',
          backdropFilter: 'blur(16px)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--cf-space-4)',
        }}
      >
        <div>
          <Badge variant="brand" size="sm" id="cf-dashboard-badge">Market Intelligence Overview</Badge>
          <h1 style={{ fontSize: '28px', marginTop: 'var(--cf-space-2)', marginBottom: 'var(--cf-space-1)', letterSpacing: '-0.02em' }}>
            Markets Overview & Intelligence
          </h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: 0, fontSize: '14px' }}>
            Real-time multi-asset observation, provider abstraction, and portfolio tracking.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--cf-space-3)' }}>
          <button
            id="cf-explore-markets-btn"
            onClick={() => navigate(PAGES.MARKETS)}
            style={{
              background: 'var(--cf-brand-gradient)',
              color: '#ffffff',
              padding: '10px 18px',
              borderRadius: 'var(--cf-radius-md)',
              fontWeight: 600,
              fontSize: '13px',
              boxShadow: 'var(--cf-brand-glow)',
              cursor: 'pointer',
              transition: 'opacity var(--cf-transition-fast)',
            }}
          >
            Explore Markets →
          </button>
        </div>
      </section>

      {/* KPI Cards Grid */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 'var(--cf-space-4)',
        }}
      >
        <StatWidget
          id="stat-spy"
          title="S&P 500 Index (SPY)"
          value="$510.15"
          changePercent={0.50}
          subtitle="Daily Volume: 65.0M"
        />
        <StatWidget
          id="stat-btc"
          title="Bitcoin (BTC-USD)"
          value="$65,400.00"
          changePercent={1.95}
          subtitle="24h High: $66,100.00"
        />
        <StatWidget
          id="stat-msft"
          title="Microsoft Corp (MSFT)"
          value="$420.25"
          changePercent={0.83}
          subtitle="All-Time Range Momentum"
        />
        <StatWidget
          id="stat-active-provider"
          title="Active Provider"
          value="Mock Provider"
          changePercent={0.0}
          subtitle="Status: Deterministic Simulator"
        />
      </section>

      {/* Featured Market Assets Table */}
      <Card
        id="cf-featured-assets-card"
        title="Active Market Watch"
        subtitle="Key benchmark instruments tracked across equities, cryptocurrency, and index ETFs"
        action={
          <button
            id="cf-view-all-markets-link"
            onClick={() => navigate(PAGES.MARKETS)}
            style={{
              background: 'transparent',
              color: 'var(--cf-brand-primary)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            View all markets →
          </button>
        }
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>INSTRUMENT</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>EXCHANGE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>TYPE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>PRICE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>24H CHANGE</th>
              </tr>
            </thead>
            <tbody>
              {FEATURED_ASSETS.map((asset) => (
                <tr
                  key={asset.symbol}
                  id={`asset-row-${asset.symbol}`}
                  style={{
                    borderBottom: '1px solid var(--cf-border)',
                    transition: 'background var(--cf-transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--cf-text-primary)' }}>{asset.symbol}</div>
                    <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)' }}>{asset.name}</div>
                  </td>
                  <td style={{ padding: '14px 16px', color: 'var(--cf-text-secondary)' }}>{asset.exchange}</td>
                  <td style={{ padding: '14px 16px' }}>
                    <Badge variant={asset.type === 'crypto' ? 'brand' : 'neutral'} size="sm">
                      {asset.type}
                    </Badge>
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                    {asset.price}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <span style={{ color: asset.isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 600 }}>
                      {asset.change}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
