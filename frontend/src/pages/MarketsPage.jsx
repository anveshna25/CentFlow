import { useState } from 'react'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'

const ALL_INSTRUMENTS = [
  { symbol: 'AAPL', name: 'Apple Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 185.50, change: '+0.87%', isUp: true, volume: '52.4M' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 420.25, change: '+0.83%', isUp: true, volume: '21.3M' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 175.80, change: '+1.27%', isUp: true, volume: '18.2M' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto', price: 65400.00, change: '+1.95%', isUp: true, volume: '28.5K' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto', price: 3450.00, change: '+1.77%', isUp: true, volume: '192K' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', assetType: 'etf', exchange: 'NYSE', market: 'US ETFs', price: 510.15, change: '+0.50%', isUp: true, volume: '65.0M' },
]

export function MarketsPage({ externalSearch = '' }) {
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [localSearch, setLocalSearch] = useState('')

  const activeSearch = externalSearch || localSearch

  const filteredInstruments = ALL_INSTRUMENTS.filter((inst) => {
    const matchesCategory =
      selectedCategory === 'all' || inst.assetType.toLowerCase() === selectedCategory.toLowerCase()
    const matchesSearch =
      !activeSearch ||
      inst.symbol.toLowerCase().includes(activeSearch.toLowerCase()) ||
      inst.name.toLowerCase().includes(activeSearch.toLowerCase()) ||
      inst.exchange.toLowerCase().includes(activeSearch.toLowerCase())

    return matchesCategory && matchesSearch
  })

  return (
    <div id="cf-markets-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Page Title & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Markets & Instruments</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Explore financial instruments, asset classifications, and price movements.
          </p>
        </div>

        {/* Filter Pills */}
        <div style={{ display: 'flex', gap: '8px', background: 'var(--cf-bg-surface-elevated)', padding: '4px', borderRadius: 'var(--cf-radius-lg)', border: '1px solid var(--cf-border)' }}>
          {['all', 'equity', 'crypto', 'etf'].map((cat) => (
            <button
              key={cat}
              id={`filter-tab-${cat}`}
              onClick={() => setSelectedCategory(cat)}
              style={{
                padding: '6px 14px',
                borderRadius: 'var(--cf-radius-md)',
                fontSize: '12px',
                fontWeight: 600,
                textTransform: 'capitalize',
                background: selectedCategory === cat ? 'var(--cf-brand-primary)' : 'transparent',
                color: selectedCategory === cat ? '#ffffff' : 'var(--cf-text-secondary)',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              {cat === 'all' ? 'All Assets' : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Main Table Card */}
      <Card
        id="cf-markets-table-card"
        title={`${filteredInstruments.length} Available Instruments`}
        subtitle="Sourced through CentFlow Provider Abstraction (Deterministic Engine)"
        action={
          <input
            id="cf-markets-filter-input"
            type="text"
            placeholder="Filter table..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            style={{
              background: 'var(--cf-bg-base)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '6px 12px',
              color: 'var(--cf-text-primary)',
              fontSize: '12px',
              outline: 'none',
            }}
          />
        }
      >
        {filteredInstruments.length === 0 ? (
          <div style={{ padding: 'var(--cf-space-8)', textAlign: 'center', color: 'var(--cf-text-muted)' }}>
            No instruments match the selected filter.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>SYMBOL</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>NAME</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>CATEGORY</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>EXCHANGE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>PRICE (USD)</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>24H CHANGE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>VOLUME</th>
                </tr>
              </thead>
              <tbody>
                {filteredInstruments.map((inst) => (
                  <tr
                    key={inst.symbol}
                    id={`market-inst-${inst.symbol}`}
                    style={{
                      borderBottom: '1px solid var(--cf-border)',
                      transition: 'background var(--cf-transition-fast)',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                      {inst.symbol}
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--cf-text-secondary)' }}>
                      {inst.name}
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant={inst.assetType === 'crypto' ? 'brand' : inst.assetType === 'etf' ? 'warning' : 'neutral'} size="sm">
                        {inst.assetType}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px', color: 'var(--cf-text-muted)' }}>
                      {inst.exchange}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                      ${inst.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <span style={{ color: inst.isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 600 }}>
                        {inst.change}
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', color: 'var(--cf-text-secondary)' }}>
                      {inst.volume}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
