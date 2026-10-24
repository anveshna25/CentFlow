import { Card } from '../components/common/Card'
import { StatWidget } from '../components/market/StatWidget'
import { Badge } from '../components/common/Badge'

const SAMPLE_POSITIONS = [
  { symbol: 'AAPL', name: 'Apple Inc.', qty: '50.00', avgPrice: '$175.20', curPrice: '$185.50', value: '$9,275.00', pnl: '+$515.00', pnlPct: '+5.88%', isUp: true },
  { symbol: 'MSFT', name: 'Microsoft Corporation', qty: '25.00', avgPrice: '$405.00', curPrice: '$420.25', value: '$10,506.25', pnl: '+$381.25', pnlPct: '+3.77%', isUp: true },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', qty: '0.35', avgPrice: '$61,200.00', curPrice: '$65,400.00', value: '$22,890.00', pnl: '+$1,470.00', pnlPct: '+6.86%', isUp: true },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF', qty: '30.00', avgPrice: '$498.50', curPrice: '$510.15', value: '$15,304.50', pnl: '+$349.50', pnlPct: '+2.34%', isUp: true },
]

export function PortfoliosPage() {
  return (
    <div id="cf-portfolios-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Portfolios & Holdings</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Consolidated position tracking, valuation, and return metrics.
          </p>
        </div>
        <Badge variant="brand" size="md">
          Active Portfolio: Main Multi-Asset
        </Badge>
      </div>

      {/* Portfolio Performance KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--cf-space-4)' }}>
        <StatWidget
          id="stat-portfolio-val"
          title="Total Valuation"
          value="$57,975.75"
          changePercent={4.88}
          subtitle="All positions marked to market"
        />
        <StatWidget
          id="stat-portfolio-pnl"
          title="Unrealized P&L"
          value="+$2,715.75"
          changePercent={4.88}
          subtitle="Net return on invested capital"
        />
        <StatWidget
          id="stat-cash-balance"
          title="Cash Reserves"
          value="$12,450.00"
          changePercent={0.0}
          subtitle="Available for allocation"
        />
      </div>

      {/* Positions Table */}
      <Card
        id="cf-positions-table-card"
        title="Open Positions (4 Holdings)"
        subtitle="Current asset holdings within your active portfolio"
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>INSTRUMENT</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>QUANTITY</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>AVG PRICE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>CURRENT PRICE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>MARKET VALUE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>RETURN</th>
              </tr>
            </thead>
            <tbody>
              {SAMPLE_POSITIONS.map((pos) => (
                <tr
                  key={pos.symbol}
                  id={`pos-row-${pos.symbol}`}
                  style={{
                    borderBottom: '1px solid var(--cf-border)',
                    transition: 'background var(--cf-transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td style={{ padding: '14px 16px' }}>
                    <div style={{ fontWeight: 700, color: 'var(--cf-text-primary)' }}>{pos.symbol}</div>
                    <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)' }}>{pos.name}</div>
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: 'var(--cf-text-secondary)' }}>
                    {pos.qty}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', color: 'var(--cf-text-muted)' }}>
                    {pos.avgPrice}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                    {pos.curPrice}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                    {pos.value}
                  </td>
                  <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                    <span style={{ color: pos.isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 600 }}>
                      {pos.pnl} ({pos.pnlPct})
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
