import { useState, useEffect, useCallback } from 'react'
import { StatWidget } from '../components/market/StatWidget'
import { Card, Badge, LoadingState, ErrorState } from '../components/common'
import { useNavigation } from '../state/NavigationContext'
import { PAGES } from '../state/pages'
import { getProviderStatus, getQuote } from '../api/marketData'

const DEFAULT_BENCHMARKS = [
  { symbol: 'AAPL', name: 'Apple Inc.', type: 'equity', price: '$185.50', change: '+0.87%', isUp: true, exchange: 'NASDAQ' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', type: 'equity', price: '$420.25', change: '+0.83%', isUp: true, exchange: 'NASDAQ' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', type: 'crypto', price: '$65,400.00', change: '+1.95%', isUp: true, exchange: 'Coinbase' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', type: 'crypto', price: '$3,450.00', change: '+1.77%', isUp: true, exchange: 'Coinbase' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF', type: 'etf', price: '$510.15', change: '+0.50%', isUp: true, exchange: 'NYSE' },
]

export function DashboardPage() {
  const { navigate } = useNavigation()
  const [providerStatus, setProviderStatus] = useState(null)
  const [featuredAssets, setFeaturedAssets] = useState(DEFAULT_BENCHMARKS)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadDashboardData = useCallback(async () => {
    setError(null)
    setIsLoading(true)
    try {
      // Query provider status from live backend API
      const statusRes = await getProviderStatus()
      if (statusRes?.data) {
        setProviderStatus(statusRes.data)
      }

      // Query live quotes for benchmarks from backend
      const symbols = ['AAPL', 'MSFT', 'BTC-USD', 'SPY']
      const quotePromises = symbols.map((sym) =>
        getQuote(sym).catch(() => null)
      )
      const results = await Promise.all(quotePromises)

      const updated = DEFAULT_BENCHMARKS.map((item) => {
        const found = results.find((r) => r?.data?.symbol === item.symbol)
        if (found?.data) {
          const q = found.data
          const isUp = typeof q.change === 'number' ? q.change >= 0 : !String(q.change || '').startsWith('-')
          return {
            ...item,
            price: `$${Number(q.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
            change: `${q.change_percent >= 0 ? '+' : ''}${q.change_percent}%`,
            isUp,
          }
        }
        return item
      })
      setFeaturedAssets(updated)
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false
    const fetchData = async () => {
      try {
        const statusRes = await getProviderStatus()
        if (!isCancelled && statusRes?.data) {
          setProviderStatus(statusRes.data)
        }

        const symbols = ['AAPL', 'MSFT', 'BTC-USD', 'SPY']
        const results = await Promise.all(symbols.map((s) => getQuote(s).catch(() => null)))
        if (!isCancelled) {
          const updated = DEFAULT_BENCHMARKS.map((item) => {
            const found = results.find((r) => r?.data?.symbol === item.symbol)
            if (found?.data) {
              const q = found.data
              const isUp = typeof q.change === 'number' ? q.change >= 0 : !String(q.change || '').startsWith('-')
              return {
                ...item,
                price: `$${Number(q.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
                change: `${q.change_percent >= 0 ? '+' : ''}${q.change_percent}%`,
                isUp,
              }
            }
            return item
          })
          setFeaturedAssets(updated)
        }
      } catch (err) {
        if (!isCancelled) setError(err)
      } finally {
        if (!isCancelled) setIsLoading(false)
      }
    }

    fetchData()
    return () => {
      isCancelled = true
    }
  }, [])

  return (
    <div id="cf-dashboard-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Optional Error Alert */}
      {error && (
        <ErrorState
          error={error}
          compact
          onRetry={loadDashboardData}
          id="cf-dashboard-error-banner"
        />
      )}

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
          <Badge variant="brand" size="sm" id="cf-dashboard-badge">
            {providerStatus ? `Provider: ${providerStatus.name.toUpperCase()} (Online)` : 'Market Intelligence Overview'}
          </Badge>
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

      {/* Loading state indicator */}
      {isLoading && (
        <LoadingState
          title="Synchronizing live quotes with backend..."
          size="sm"
          id="cf-dash-spinner"
        />
      )}

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
          value={featuredAssets.find((a) => a.symbol === 'SPY')?.price || '$510.15'}
          changePercent={0.50}
          subtitle="Daily Volume: 65.0M"
        />
        <StatWidget
          id="stat-btc"
          title="Bitcoin (BTC-USD)"
          value={featuredAssets.find((a) => a.symbol === 'BTC-USD')?.price || '$65,400.00'}
          changePercent={1.95}
          subtitle="24h High: $66,100.00"
        />
        <StatWidget
          id="stat-msft"
          title="Microsoft Corp (MSFT)"
          value={featuredAssets.find((a) => a.symbol === 'MSFT')?.price || '$420.25'}
          changePercent={0.83}
          subtitle="All-Time Range Momentum"
        />
        <StatWidget
          id="stat-active-provider"
          title="Active Provider"
          value={providerStatus ? providerStatus.name.toUpperCase() : 'MOCK'}
          changePercent={0.0}
          subtitle={providerStatus?.message || 'Status: Deterministic Simulator'}
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
              {featuredAssets.map((asset) => (
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
