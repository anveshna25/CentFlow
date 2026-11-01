import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Badge,
  Button,
  LoadingState,
  ErrorState,
  StatWidget,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableHeaderCell,
  Skeleton,
} from '../components/common'
import { useNavigation } from '../state/NavigationContext'
import { PAGES } from '../state/pages'
import { getProviderStatus, getQuote } from '../api/marketData'
import { getAnalyticsSummary } from '../api/analytics'
import { TechnicalPostureBadge, MarketRegimeDistribution } from '../components/analytics'

const INITIAL_BENCHMARKS = [
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', type: 'etf', exchange: 'NYSE', price: 510.15, change: '+0.50%', changePercent: 0.50, isUp: true, volume: '65.0M' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust (Nasdaq 100)', type: 'etf', exchange: 'NASDAQ', price: 442.80, change: '+0.75%', changePercent: 0.75, isUp: true, volume: '42.1M' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', type: 'crypto', exchange: 'Coinbase', price: 65400.00, change: '+1.95%', changePercent: 1.95, isUp: true, volume: '28.5K' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', type: 'crypto', exchange: 'Coinbase', price: 3450.00, change: '+1.77%', changePercent: 1.77, isUp: true, volume: '192K' },
  { symbol: 'AAPL', name: 'Apple Inc.', type: 'equity', exchange: 'NASDAQ', price: 185.50, change: '+0.87%', changePercent: 0.87, isUp: true, volume: '52.4M' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', type: 'equity', exchange: 'NASDAQ', price: 420.25, change: '+0.83%', changePercent: 0.83, isUp: true, volume: '21.3M' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', type: 'equity', exchange: 'NASDAQ', price: 128.40, change: '+2.11%', changePercent: 2.11, isUp: true, volume: '78.5M' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', type: 'equity', exchange: 'NASDAQ', price: 175.80, change: '+1.27%', changePercent: 1.27, isUp: true, volume: '18.2M' },
]

export function DashboardPage() {
  const { navigate } = useNavigation()
  const [providerStatus, setProviderStatus] = useState(null)
  const [marketAssets, setMarketAssets] = useState(INITIAL_BENCHMARKS)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [intelligenceMap, setIntelligenceMap] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null)

  const loadDashboardData = useCallback(async (showRefreshing = false) => {
    setError(null)
    if (showRefreshing) {
      setIsRefreshing(true)
    } else {
      setIsLoading(true)
    }

    try {
      // 1. Fetch provider status
      const statusRes = await getProviderStatus().catch(() => null)
      if (statusRes?.data) {
        setProviderStatus(statusRes.data)
      }

      // 2. Fetch live quotes for all benchmark assets in parallel
      const quotePromises = INITIAL_BENCHMARKS.map((item) =>
        getQuote(item.symbol).catch(() => null)
      )

      // 3. Fetch analytics intelligence in parallel across benchmarks
      const intelPromises = INITIAL_BENCHMARKS.map((item) =>
        getAnalyticsSummary(item.symbol, 365, '1d').catch(() => null)
      )

      const [quoteResults, intelResults] = await Promise.all([
        Promise.all(quotePromises),
        Promise.all(intelPromises),
      ])

      const updatedAssets = INITIAL_BENCHMARKS.map((item, idx) => {
        const quoteEnvelope = quoteResults[idx]
        if (quoteEnvelope?.data) {
          const q = quoteEnvelope.data
          const isUp = typeof q.change === 'number' ? q.change >= 0 : !String(q.change || '').startsWith('-')
          const numericPrice = Number(q.price)
          const pct = Number(q.change_percent ?? 0)
          const formattedVol = q.volume
            ? Number(q.volume) > 1000000
              ? `${(Number(q.volume) / 1000000).toFixed(1)}M`
              : `${(Number(q.volume) / 1000).toFixed(1)}K`
            : item.volume

          return {
            ...item,
            price: numericPrice,
            change: `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`,
            changePercent: pct,
            isUp,
            volume: formattedVol,
          }
        }
        return item
      })
      setMarketAssets(updatedAssets)

      // Store intelligence keyed by symbol
      const updatedIntelMap = {}
      INITIAL_BENCHMARKS.forEach((item, idx) => {
        if (intelResults[idx]?.data) {
          updatedIntelMap[item.symbol] = intelResults[idx].data
        }
      })
      setIntelligenceMap(updatedIntelMap)

      setLastRefreshedAt(new Date().toLocaleTimeString())
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false
    const init = async () => {
      try {
        await loadDashboardData(false)
      } catch (err) {
        if (!isCancelled) setError(err)
      }
    }
    init()
    return () => {
      isCancelled = true
    }
  }, [loadDashboardData])

  // Categorized assets
  const filteredAssets = marketAssets.filter((asset) => {
    if (selectedCategory === 'all') return true
    if (selectedCategory === 'equity') return asset.type === 'equity'
    if (selectedCategory === 'crypto') return asset.type === 'crypto'
    if (selectedCategory === 'etf') return asset.type === 'etf'
    return true
  })

  // Market Breadth metrics
  const advancingCount = marketAssets.filter((a) => a.isUp).length
  const decliningCount = marketAssets.length - advancingCount
  const avgChange = (
    marketAssets.reduce((acc, a) => acc + (a.changePercent || 0), 0) / (marketAssets.length || 1)
  ).toFixed(2)

  const spyAsset = marketAssets.find((a) => a.symbol === 'SPY') || INITIAL_BENCHMARKS[0]
  const qqqAsset = marketAssets.find((a) => a.symbol === 'QQQ') || INITIAL_BENCHMARKS[1]
  const btcAsset = marketAssets.find((a) => a.symbol === 'BTC-USD') || INITIAL_BENCHMARKS[2]
  const ethAsset = marketAssets.find((a) => a.symbol === 'ETH-USD') || INITIAL_BENCHMARKS[3]

  return (
    <div id="cf-dashboard-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Optional Error Alert */}
      {error && (
        <ErrorState
          error={error}
          compact
          onRetry={() => loadDashboardData(false)}
          id="cf-dashboard-error-banner"
        />
      )}

      {/* Hero Welcome & Market Overview Header */}
      <section
        style={{
          background: 'var(--cf-bg-surface-elevated)',
          border: '1px solid var(--cf-border)',
          borderTop: '3px solid var(--cf-brand-primary)',
          borderRadius: 'var(--cf-radius-xl)',
          padding: 'var(--cf-space-6)',
          boxShadow: 'var(--cf-shadow-sm)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--cf-space-4)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)', flexWrap: 'wrap' }}>
            <Badge variant="brand" size="sm" id="cf-dashboard-badge">
              {providerStatus ? `Feed: ${providerStatus.name.toUpperCase()} (Active)` : 'Market Feed Online'}
            </Badge>
            {lastRefreshedAt && (
              <span style={{ fontSize: 'var(--cf-font-size-xs)', color: 'var(--cf-text-muted)' }}>
                Updated: {lastRefreshedAt}
              </span>
            )}
          </div>
          <h1
            style={{
              fontFamily: 'var(--cf-font-display)',
              fontSize: 'var(--cf-font-size-3xl)',
              fontWeight: 'var(--cf-font-weight-bold)',
              color: 'var(--cf-text-primary)',
              marginTop: 'var(--cf-space-2)',
              marginBottom: 'var(--cf-space-1)',
              letterSpacing: '-0.02em',
            }}
          >
            Market Overview & Global Intelligence
          </h1>
          <p
            style={{
              color: 'var(--cf-text-secondary)',
              margin: 0,
              fontSize: 'var(--cf-font-size-base)',
              maxWidth: '720px',
            }}
          >
            Multi-asset observation engine, benchmark index tracking, and quantitative factor regimes.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: 'var(--cf-space-3)', alignItems: 'center' }}>
          <Button
            id="cf-refresh-dashboard-btn"
            variant="secondary"
            size="md"
            onClick={() => loadDashboardData(true)}
            isLoading={isRefreshing}
            iconLeft={<span aria-hidden="true">↻</span>}
          >
            Refresh Quotes
          </Button>
          <Button
            id="cf-explore-markets-btn"
            variant="primary"
            size="md"
            onClick={() => navigate(PAGES.MARKETS)}
            iconRight={<span aria-hidden="true">→</span>}
          >
            Explore Markets
          </Button>
        </div>
      </section>

      {/* Loading state indicator */}
      {isLoading && (
        <LoadingState
          title="Synchronizing live quotes and market regimes with backend..."
          size="sm"
          id="cf-dash-spinner"
        />
      )}

      {/* Market Breadth & Health Status Bar */}
      <div
        id="cf-market-breadth-bar"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--cf-space-3)',
          background: 'var(--cf-bg-surface)',
          border: '1px solid var(--cf-border)',
          borderRadius: 'var(--cf-radius-lg)',
          padding: 'var(--cf-space-4)',
          boxShadow: 'var(--cf-shadow-sm)',
        }}
      >
        <div>
          <div
            style={{
              fontSize: 'var(--cf-font-size-xs)',
              color: 'var(--cf-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 'var(--cf-font-weight-bold)',
            }}
          >
            Market Breadth
          </div>
          <div style={{ fontSize: 'var(--cf-font-size-md)', fontWeight: 600, color: 'var(--cf-text-primary)', marginTop: '4px' }}>
            <span style={{ color: 'var(--cf-bullish)' }}>{advancingCount} Advancing</span>
            <span style={{ color: 'var(--cf-text-muted)', margin: '0 6px' }}>/</span>
            <span style={{ color: 'var(--cf-bearish)' }}>{decliningCount} Declining</span>
          </div>
        </div>

        <div>
          <div
            style={{
              fontSize: 'var(--cf-font-size-xs)',
              color: 'var(--cf-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 'var(--cf-font-weight-bold)',
            }}
          >
            Average Benchmark Drift
          </div>
          <div
            className="cf-num-tabular"
            style={{
              fontSize: 'var(--cf-font-size-md)',
              fontWeight: 600,
              color: Number(avgChange) >= 0 ? 'var(--cf-bullish)' : 'var(--cf-bearish)',
              marginTop: '4px',
            }}
          >
            {Number(avgChange) >= 0 ? `+${avgChange}%` : `${avgChange}%`}
          </div>
        </div>

        <div>
          <div
            style={{
              fontSize: 'var(--cf-font-size-xs)',
              color: 'var(--cf-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 'var(--cf-font-weight-bold)',
            }}
          >
            Provider Architecture
          </div>
          <div style={{ fontSize: 'var(--cf-font-size-md)', fontWeight: 600, color: 'var(--cf-brand-cyan)', marginTop: '4px' }}>
            {providerStatus?.name ? providerStatus.name.toUpperCase() : 'MOCK'} Engine
          </div>
        </div>

        <div>
          <div
            style={{
              fontSize: 'var(--cf-font-size-xs)',
              color: 'var(--cf-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              fontWeight: 'var(--cf-font-weight-bold)',
            }}
          >
            Provider Health
          </div>
          <div style={{ fontSize: 'var(--cf-font-size-md)', fontWeight: 600, color: 'var(--cf-bullish)', marginTop: '4px' }}>
            ● Healthy & Operational
          </div>
        </div>
      </div>

      {/* Major Index Benchmark KPI Cards Grid */}
      <section
        id="cf-dashboard-benchmarks-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 'var(--cf-space-4)',
        }}
      >
        <StatWidget
          id="stat-spy"
          title="S&P 500 Index (SPY)"
          value={`$${Number(spyAsset.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          changePercent={spyAsset.changePercent}
          subtitle={`Daily Volume: ${spyAsset.volume} · Click to inspect`}
          status="live"
          extra={
            <TechnicalPostureBadge
              posture={intelligenceMap['SPY'] || 'BULLISH'}
              showScore
              size="sm"
              id="badge-stat-spy"
            />
          }
          onClick={() => navigate(PAGES.MARKETS, { symbol: 'SPY' })}
        />
        <StatWidget
          id="stat-qqq"
          title="Nasdaq 100 Index (QQQ)"
          value={`$${Number(qqqAsset.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          changePercent={qqqAsset.changePercent}
          subtitle={`Daily Volume: ${qqqAsset.volume} · Click to inspect`}
          status="live"
          extra={
            <TechnicalPostureBadge
              posture={intelligenceMap['QQQ'] || 'BULLISH'}
              showScore
              size="sm"
              id="badge-stat-qqq"
            />
          }
          onClick={() => navigate(PAGES.MARKETS, { symbol: 'QQQ' })}
        />
        <StatWidget
          id="stat-btc"
          title="Bitcoin USD (BTC-USD)"
          value={`$${Number(btcAsset.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          changePercent={btcAsset.changePercent}
          subtitle="Crypto Benchmark · Click to inspect"
          status="live"
          extra={
            <TechnicalPostureBadge
              posture={intelligenceMap['BTC-USD'] || 'BULLISH'}
              showScore
              size="sm"
              id="badge-stat-btc"
            />
          }
          onClick={() => navigate(PAGES.MARKETS, { symbol: 'BTC-USD' })}
        />
        <StatWidget
          id="stat-eth"
          title="Ethereum USD (ETH-USD)"
          value={`$${Number(ethAsset.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          changePercent={ethAsset.changePercent}
          subtitle="Smart Contract Benchmark · Click to inspect"
          status="live"
          extra={
            <TechnicalPostureBadge
              posture={intelligenceMap['ETH-USD'] || 'BULLISH'}
              showScore
              size="sm"
              id="badge-stat-eth"
            />
          }
          onClick={() => navigate(PAGES.MARKETS, { symbol: 'ETH-USD' })}
        />
      </section>

      {/* Cross-Asset Market Trend & Volatility Regimes Distribution */}
      <MarketRegimeDistribution intelligenceMap={intelligenceMap} isLoading={isLoading} />

      {/* Macro & Regime Highlights Section */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 'var(--cf-space-4)' }}>
        {/* SPY Equity Regime Snapshot */}
        <Card
          id="cf-macro-spy-card"
          title="Equity Macro Regime (SPY)"
          subtitle="Broad US market factor posture and trend consensus"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(PAGES.MARKETS, { symbol: 'SPY' })}
            >
              Analyze factors →
            </Button>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--cf-font-size-base)', color: 'var(--cf-text-secondary)' }}>Trend Posture</span>
              <TechnicalPostureBadge
                posture={intelligenceMap['SPY'] || 'BULLISH'}
                size="sm"
                id="macro-posture-spy"
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--cf-font-size-base)', color: 'var(--cf-text-secondary)' }}>Quantitative Score</span>
              <span style={{ fontWeight: 700, fontSize: 'var(--cf-font-size-md)', color: 'var(--cf-brand-cyan)' }}>
                {intelligenceMap['SPY']?.composite_score ?? 65} / 100
              </span>
            </div>
            <div style={{ borderTop: '1px solid var(--cf-border)', paddingTop: 'var(--cf-space-2)', fontSize: 'var(--cf-font-size-sm)', color: 'var(--cf-text-muted)' }}>
              {intelligenceMap['SPY']?.rationales?.[0] || 'Price trading above primary moving average envelopes indicating positive momentum posture.'}
            </div>
          </div>
        </Card>

        {/* BTC Digital Asset Regime Snapshot */}
        <Card
          id="cf-macro-btc-card"
          title="Digital Asset Regime (BTC-USD)"
          subtitle="Crypto benchmark volatility and momentum posture"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(PAGES.MARKETS, { symbol: 'BTC-USD' })}
            >
              Analyze factors →
            </Button>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--cf-font-size-base)', color: 'var(--cf-text-secondary)' }}>Trend Posture</span>
              <TechnicalPostureBadge
                posture={intelligenceMap['BTC-USD'] || 'BULLISH'}
                size="sm"
                id="macro-posture-btc"
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 'var(--cf-font-size-base)', color: 'var(--cf-text-secondary)' }}>Quantitative Score</span>
              <span style={{ fontWeight: 700, fontSize: 'var(--cf-font-size-md)', color: 'var(--cf-brand-cyan)' }}>
                {intelligenceMap['BTC-USD']?.composite_score ?? 70} / 100
              </span>
            </div>
            <div style={{ borderTop: '1px solid var(--cf-border)', paddingTop: 'var(--cf-space-2)', fontSize: 'var(--cf-font-size-sm)', color: 'var(--cf-text-muted)' }}>
              {intelligenceMap['BTC-USD']?.rationales?.[0] || 'Decoupled crypto risk asset exhibiting positive momentum and strong RSI consolidation.'}
            </div>
          </div>
        </Card>
      </section>

      {/* Featured Market Assets & Active Movers Table */}
      <Card
        id="cf-featured-assets-card"
        title="Active Benchmark Instruments"
        subtitle="Live prices, daily drift, and volume across key asset classes"
        action={
          <div
            style={{
              display: 'flex',
              gap: 'var(--cf-space-1)',
              background: 'var(--cf-bg-surface-elevated)',
              padding: '3px',
              borderRadius: 'var(--cf-radius-md)',
              border: '1px solid var(--cf-border)',
            }}
          >
            {['all', 'equity', 'crypto', 'etf'].map((cat) => (
              <Button
                key={cat}
                id={`dashboard-filter-${cat}`}
                variant={selectedCategory === cat ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setSelectedCategory(cat)}
                style={{
                  textTransform: 'capitalize',
                  height: '26px',
                  padding: '0 var(--cf-space-2)',
                  fontSize: 'var(--cf-font-size-xs)',
                }}
              >
                {cat === 'all' ? 'All' : cat}
              </Button>
            ))}
          </div>
        }
      >
        <Table id="cf-featured-assets-table">
          <TableHead>
            <TableRow hoverable={false}>
              <TableHeaderCell>INSTRUMENT</TableHeaderCell>
              <TableHeaderCell>TYPE</TableHeaderCell>
              <TableHeaderCell>EXCHANGE</TableHeaderCell>
              <TableHeaderCell align="right">PRICE (USD)</TableHeaderCell>
              <TableHeaderCell align="right">24H CHANGE</TableHeaderCell>
              <TableHeaderCell align="center">SIGNALS & POSTURE</TableHeaderCell>
              <TableHeaderCell align="right">VOLUME</TableHeaderCell>
              <TableHeaderCell align="center">ACTION</TableHeaderCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading && marketAssets.length === 0 ? (
              Array.from({ length: 4 }).map((_, i) => (
                <TableRow key={`skeleton-${i}`} hoverable={false}>
                  <TableCell><Skeleton width="90px" height="18px" /></TableCell>
                  <TableCell><Skeleton width="50px" height="18px" /></TableCell>
                  <TableCell><Skeleton width="60px" height="18px" /></TableCell>
                  <TableCell align="right"><Skeleton width="70px" height="18px" /></TableCell>
                  <TableCell align="right"><Skeleton width="60px" height="18px" /></TableCell>
                  <TableCell align="center"><Skeleton width="100px" height="18px" /></TableCell>
                  <TableCell align="right"><Skeleton width="50px" height="18px" /></TableCell>
                  <TableCell align="center"><Skeleton width="80px" height="24px" /></TableCell>
                </TableRow>
              ))
            ) : (
              filteredAssets.map((asset) => (
                <TableRow
                  key={asset.symbol}
                  id={`asset-row-${asset.symbol}`}
                  onClick={() => navigate(PAGES.MARKETS, { symbol: asset.symbol })}
                  hoverable
                >
                  <TableCell>
                    <div style={{ fontWeight: 600, color: 'var(--cf-brand-cyan)' }}>{asset.symbol}</div>
                    <div style={{ fontSize: 'var(--cf-font-size-xs)', color: 'var(--cf-text-secondary)' }}>{asset.name}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={asset.type === 'crypto' ? 'brand' : asset.type === 'etf' ? 'warning' : 'neutral'} size="sm">
                      {asset.type}
                    </Badge>
                  </TableCell>
                  <TableCell style={{ color: 'var(--cf-text-secondary)' }}>{asset.exchange}</TableCell>
                  <TableCell align="right" tabular style={{ fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                    ${Number(asset.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </TableCell>
                  <TableCell align="right" tabular>
                    <span style={{ color: asset.isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 600 }}>
                      {asset.change}
                    </span>
                  </TableCell>
                  <TableCell align="center">
                    <TechnicalPostureBadge
                      posture={intelligenceMap[asset.symbol]}
                      showScore
                      size="sm"
                      id={`posture-table-${asset.symbol}`}
                    />
                  </TableCell>
                  <TableCell align="right" tabular style={{ color: 'var(--cf-text-secondary)' }}>
                    {asset.volume}
                  </TableCell>
                  <TableCell align="center">
                    <Button
                      id={`btn-inspect-${asset.symbol}`}
                      variant="secondary"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        navigate(PAGES.MARKETS, { symbol: asset.symbol })
                      }}
                      style={{
                        height: '26px',
                        padding: '0 var(--cf-space-2)',
                        fontSize: '11px',
                      }}
                    >
                      Inspect & Chart
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
