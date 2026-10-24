import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'

const SAMPLE_WATCHLISTS = [
  {
    id: 'wl-tech',
    name: 'Mega-Cap Technology',
    description: 'High-conviction core enterprise technology holdings',
    items: ['AAPL', 'MSFT', 'GOOGL'],
    dailyChange: '+0.95%',
    isUp: true,
  },
  {
    id: 'wl-crypto',
    name: 'Decentralized Layer 1s',
    description: 'Dominant smart contract platforms and monetary store-of-value',
    items: ['BTC-USD', 'ETH-USD'],
    dailyChange: '+1.86%',
    isUp: true,
  },
  {
    id: 'wl-macro',
    name: 'Macro & Index Hedges',
    description: 'Broad equity benchmarks and liquid ETF hedges',
    items: ['SPY'],
    dailyChange: '+0.50%',
    isUp: true,
  },
]

export function WatchlistsPage() {
  return (
    <div id="cf-watchlists-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Watchlists</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Monitor tailored collections of instruments across multiple asset classes.
          </p>
        </div>
        <button
          id="cf-new-watchlist-btn"
          style={{
            background: 'var(--cf-bg-surface-elevated)',
            color: 'var(--cf-text-primary)',
            border: '1px solid var(--cf-border)',
            borderRadius: 'var(--cf-radius-md)',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          + New Watchlist
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--cf-space-5)' }}>
        {SAMPLE_WATCHLISTS.map((wl) => (
          <Card
            key={wl.id}
            id={`watchlist-card-${wl.id}`}
            title={wl.name}
            subtitle={wl.description}
            hoverable
            action={
              <Badge variant={wl.isUp ? 'bullish' : 'bearish'} size="sm">
                {wl.dailyChange}
              </Badge>
            }
          >
            <div style={{ marginTop: 'var(--cf-space-3)' }}>
              <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Tracked Symbols ({wl.items.length})
              </span>
              <div style={{ display: 'flex', gap: '8px', marginTop: '8px', flexWrap: 'wrap' }}>
                {wl.items.map((sym) => (
                  <span
                    key={sym}
                    style={{
                      background: 'var(--cf-bg-base)',
                      border: '1px solid var(--cf-border)',
                      borderRadius: 'var(--cf-radius-sm)',
                      padding: '4px 10px',
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--cf-text-primary)',
                    }}
                  >
                    {sym}
                  </span>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
