import { useState, useEffect, useCallback, useTransition, useRef } from 'react'
import { Card, Badge, LoadingState, ErrorState, EmptyState } from '../components/common'
import { AssetDetailModal } from '../components/market/AssetDetailModal'
import { useNavigation } from '../state/NavigationContext'
import {
  searchInstruments,
  getQuote,
  getHistoricalBars,
  ingestQuote,
  backfillHistoricalBars,
} from '../api/marketData'
import {
  getAnalyticsSummary,
  getIndicatorSeries,
  getReturnsAnalysis,
} from '../api/analytics'
import { getDefaultWatchlist, addToWatchlist, removeFromWatchlist } from '../api/watchlist'

const DEFAULT_INSTRUMENTS = [
  { symbol: 'AAPL', name: 'Apple Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 185.50, change: '+0.87%', isUp: true, volume: '52.4M' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 420.25, change: '+0.83%', isUp: true, volume: '21.3M' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities', price: 175.80, change: '+1.27%', isUp: true, volume: '18.2M' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto', price: 65400.00, change: '+1.95%', isUp: true, volume: '28.5K' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto', price: 3450.00, change: '+1.77%', isUp: true, volume: '192K' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', assetType: 'etf', exchange: 'NYSE', market: 'US ETFs', price: 510.15, change: '+0.50%', isUp: true, volume: '65.0M' },
]

const TIMEFRAME_CONFIG = {
  '1D': { days: 1, interval: '1d' },
  '1W': { days: 7, interval: '1d' },
  '1M': { days: 30, interval: '1d' },
  '1Y': { days: 365, interval: '1d' },
  ALL: { days: 365, interval: '1d' },
}

export function MarketsPage({ externalSearch = '' }) {
  const { pageParams } = useNavigation()
  const [, startTransition] = useTransition()
  const autoOpenedSymbolRef = useRef(null)
  const [instruments, setInstruments] = useState(DEFAULT_INSTRUMENTS)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [localSearch, setLocalSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [watchlistId, setWatchlistId] = useState(null)
  const [isInWatchlist, setIsInWatchlist] = useState(false)

  // Selected Instrument Detail & Chart State
  const [selectedInstrument, setSelectedInstrument] = useState(null)
  const [quoteDetail, setQuoteDetail] = useState(null)
  const [chartBars, setChartBars] = useState([])
  const [chartTimeframe, setChartTimeframe] = useState('1M')
  const [isChartLoading, setIsChartLoading] = useState(false)
  const [actionFeedback, setActionFeedback] = useState(null)

  // Analytics & Quantitative Intelligence State
  const [indicatorsData, setIndicatorsData] = useState(null)
  const [intelligenceDetail, setIntelligenceDetail] = useState(null)
  const [returnsData, setReturnsData] = useState(null)
  const [isIntelligenceLoading, setIsIntelligenceLoading] = useState(false)

  const activeSearch = externalSearch || debouncedSearch

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(localSearch.trim())
    }, 300)
    return () => clearTimeout(handler)
  }, [localSearch])

  // Initial and on-demand load of instruments
  const loadInstruments = useCallback(async () => {
    setError(null)
    setIsLoading(true)
    try {
      const res = await searchInstruments(activeSearch)
      if (res?.data && res.data.length > 0) {
        const enriched = await Promise.all(
          res.data.map(async (inst) => {
            try {
              const quoteRes = await getQuote(inst.symbol)
              const q = quoteRes?.data
              if (q) {
                const isUp = typeof q.change === 'number' ? q.change >= 0 : !String(q.change || '').startsWith('-')
                return {
                  symbol: inst.symbol,
                  name: inst.name,
                  assetType: inst.asset_type || 'equity',
                  exchange: inst.exchange || 'N/A',
                  market: inst.market || 'Global',
                  price: Number(q.price),
                  change: `${q.change_percent >= 0 ? '+' : ''}${q.change_percent}%`,
                  isUp,
                  volume: q.volume ? `${(Number(q.volume) / 1000000).toFixed(1)}M` : 'N/A',
                }
              }
            } catch {
              // Ignore individual quote errors
            }
            return {
              symbol: inst.symbol,
              name: inst.name,
              assetType: inst.asset_type || 'equity',
              exchange: inst.exchange || 'N/A',
              market: inst.market || 'Global',
              price: 0,
              change: '0.00%',
              isUp: true,
              volume: 'N/A',
            }
          })
        )
        setInstruments(enriched)
      }
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
    }
  }, [activeSearch])

  useEffect(() => {
    let isCancelled = false
    const fetchCatalog = async () => {
      try {
        const res = await searchInstruments(activeSearch)
        if (!isCancelled && res?.data && res.data.length > 0) {
          const enriched = await Promise.all(
            res.data.map(async (inst) => {
              try {
                const quoteRes = await getQuote(inst.symbol)
                const q = quoteRes?.data
                if (q) {
                  const isUp = typeof q.change === 'number' ? q.change >= 0 : !String(q.change || '').startsWith('-')
                  return {
                    symbol: inst.symbol,
                    name: inst.name,
                    assetType: inst.asset_type || 'equity',
                    exchange: inst.exchange || 'N/A',
                    market: inst.market || 'Global',
                    price: Number(q.price),
                    change: `${q.change_percent >= 0 ? '+' : ''}${q.change_percent}%`,
                    isUp,
                    volume: q.volume ? `${(Number(q.volume) / 1000000).toFixed(1)}M` : 'N/A',
                  }
                }
              } catch {
                // Ignore individual quote error
              }
              return {
                symbol: inst.symbol,
                name: inst.name,
                assetType: inst.asset_type || 'equity',
                exchange: inst.exchange || 'N/A',
                market: inst.market || 'Global',
                price: 0,
                change: '0.00%',
                isUp: true,
                volume: 'N/A',
              }
            })
          )
          if (!isCancelled) {
            setInstruments(enriched)
          }
        }
      } catch (err) {
        if (!isCancelled) setError(err)
      }
    }

    fetchCatalog()
    return () => {
      isCancelled = true
    }
  }, [activeSearch])

  // Load historical bars, indicators, quote, and market intelligence when selecting an instrument
  useEffect(() => {
    if (!selectedInstrument) return
    let isCancelled = false

    const fetchDetailData = async () => {
      setIsChartLoading(true)
      setIsIntelligenceLoading(true)
      const config = TIMEFRAME_CONFIG[chartTimeframe] || TIMEFRAME_CONFIG['1M']
      const lookbackDays = config.days === 1 ? 30 : config.days

      try {
        const [barsRes, quoteRes, indicatorsRes, summaryRes, returnsRes] = await Promise.all([
          getHistoricalBars(selectedInstrument.symbol, config.days, config.interval).catch(() => null),
          getQuote(selectedInstrument.symbol).catch(() => null),
          getIndicatorSeries(selectedInstrument.symbol, lookbackDays, config.interval, {
            includeRsi: true,
            includeMacd: true,
            includeBollinger: true,
          }).catch(() => null),
          getAnalyticsSummary(selectedInstrument.symbol, lookbackDays, config.interval).catch(() => null),
          getReturnsAnalysis(selectedInstrument.symbol, lookbackDays, config.interval, 252).catch(() => null),
        ])

        if (!isCancelled) {
          if (barsRes?.data) setChartBars(barsRes.data)
          if (quoteRes?.data) setQuoteDetail(quoteRes.data)
          if (indicatorsRes?.data) setIndicatorsData(indicatorsRes.data)
          if (summaryRes?.data) setIntelligenceDetail(summaryRes.data)
          if (returnsRes?.data) setReturnsData(returnsRes.data)
        }
      } finally {
        if (!isCancelled) {
          setIsChartLoading(false)
          setIsIntelligenceLoading(false)
        }
      }
    }

    fetchDetailData()
    return () => {
      isCancelled = true
    }
  }, [selectedInstrument, chartTimeframe])

  const handleOpenDetail = useCallback((inst) => {
    startTransition(() => {
      setSelectedInstrument(inst)
      setIsInWatchlist(false)
      setActionFeedback(null)
    })
  }, [])

  // Auto-open detail modal if navigated with symbol param (e.g. from Dashboard or Search)
  useEffect(() => {
    const symbolParam = pageParams?.symbol
    if (!symbolParam || autoOpenedSymbolRef.current === symbolParam) return

    autoOpenedSymbolRef.current = symbolParam
    const match = instruments.find((i) => i.symbol.toUpperCase() === symbolParam.toUpperCase())
    if (match) {
      handleOpenDetail(match)
    } else {
      handleOpenDetail({
        symbol: symbolParam.toUpperCase(),
        name: pageParams?.name || symbolParam.toUpperCase(),
        assetType: pageParams?.assetType || 'equity',
        exchange: pageParams?.exchange || 'N/A',
        market: 'Global',
        price: 0,
        change: '0.00%',
        isUp: true,
        volume: 'N/A',
      })
    }
  }, [pageParams?.symbol, pageParams?.name, pageParams?.assetType, pageParams?.exchange, instruments, handleOpenDetail])

  const handleCloseDetail = () => {
    setSelectedInstrument(null)
    setIsInWatchlist(false)
    setQuoteDetail(null)
    setChartBars([])
    setIndicatorsData(null)
    setIntelligenceDetail(null)
    setReturnsData(null)
    setActionFeedback(null)
  }

  // Load default watchlist on mount
  useEffect(() => {
    let isCancelled = false
    getDefaultWatchlist()
      .then((wl) => {
        if (!isCancelled && wl?.id) setWatchlistId(wl.id)
      })
      .catch(() => {})
    return () => {
      isCancelled = true
    }
  }, [])

  // Check if selected instrument is in watchlist
  useEffect(() => {
    if (!selectedInstrument || !watchlistId) return

    let isCancelled = false
    getDefaultWatchlist()
      .then((wl) => {
        if (!isCancelled && wl?.items) {
          const exists = wl.items.some(
            (item) => item.symbol.toUpperCase() === selectedInstrument.symbol.toUpperCase()
          )
          setIsInWatchlist(exists)
        }
      })
      .catch(() => {})
    return () => {
      isCancelled = true
    }
  }, [selectedInstrument, watchlistId])


  const handleToggleWatchlist = async () => {
    if (!selectedInstrument || !watchlistId) return
    try {
      if (isInWatchlist) {
        await removeFromWatchlist(watchlistId, selectedInstrument.symbol)
        setIsInWatchlist(false)
        setActionFeedback({ type: 'info', message: `Removed ${selectedInstrument.symbol} from watchlist.` })
      } else {
        await addToWatchlist(watchlistId, selectedInstrument.symbol)
        setIsInWatchlist(true)
        setActionFeedback({ type: 'success', message: `Added ${selectedInstrument.symbol} to watchlist!` })
      }
    } catch (err) {
      setActionFeedback({ type: 'error', message: err.message || 'Watchlist action failed.' })
    }
  }

  const handlePersistQuote = async () => {
    if (!selectedInstrument) return
    try {
      setActionFeedback({ type: 'info', message: 'Persisting quote to database...' })
      const res = await ingestQuote(selectedInstrument.symbol)
      if (res?.data) {
        setActionFeedback({ type: 'success', message: `Quote for ${selectedInstrument.symbol} persisted durably.` })
      }
    } catch {
      setActionFeedback({ type: 'error', message: 'Failed to persist quote.' })
    }
  }

  const handleBackfillBars = async () => {
    if (!selectedInstrument) return
    try {
      setActionFeedback({ type: 'info', message: 'Backfilling 30-day bars to database...' })
      const res = await backfillHistoricalBars(selectedInstrument.symbol, 30, '1d')
      if (res?.data) {
        setActionFeedback({
          type: 'success',
          message: `Backfilled ${res.data.bars_ingested} bars for ${selectedInstrument.symbol}. Refreshing calculations...`,
        })

        // Refresh analytics and chart data
        const config = TIMEFRAME_CONFIG[chartTimeframe] || TIMEFRAME_CONFIG['1M']
        const lookbackDays = config.days === 1 ? 30 : config.days
        const [barsRes, indicatorsRes, summaryRes, returnsRes] = await Promise.all([
          getHistoricalBars(selectedInstrument.symbol, config.days, config.interval).catch(() => null),
          getIndicatorSeries(selectedInstrument.symbol, lookbackDays, config.interval, {
            includeRsi: true,
            includeMacd: true,
            includeBollinger: true,
          }).catch(() => null),
          getAnalyticsSummary(selectedInstrument.symbol, lookbackDays, config.interval).catch(() => null),
          getReturnsAnalysis(selectedInstrument.symbol, lookbackDays, config.interval, 252).catch(() => null),
        ])
        if (barsRes?.data) setChartBars(barsRes.data)
        if (indicatorsRes?.data) setIndicatorsData(indicatorsRes.data)
        if (summaryRes?.data) setIntelligenceDetail(summaryRes.data)
        if (returnsRes?.data) setReturnsData(returnsRes.data)
      }
    } catch {
      setActionFeedback({ type: 'error', message: 'Failed to backfill bars.' })
    }
  }

  const filteredInstruments = instruments.filter((inst) => {
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
      {/* Optional Error Alert */}
      {error && (
        <ErrorState
          error={error}
          compact
          onRetry={loadInstruments}
          id="cf-markets-error-banner"
        />
      )}

      {/* Page Title & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Markets & Instruments</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Explore financial instruments, asset classifications, and interactive OHLCV charts.
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
                border: 'none',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              {cat === 'all' ? 'All Assets' : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Loading Indicator */}
      {isLoading && (
        <LoadingState
          title="Retrieving market instruments..."
          description="Synchronizing quotes and metadata from the backend data feed"
          size="sm"
          id="cf-markets-spinner"
        />
      )}

      {/* Main Table Card */}
      <Card
        id="cf-markets-table-card"
        title={`${filteredInstruments.length} Available Instruments`}
        subtitle="Click any instrument to open interactive price chart & market intelligence"
        action={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              id="cf-markets-filter-input"
              type="text"
              placeholder="Search symbol or name..."
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
                width: '180px',
              }}
            />
          </div>
        }
      >
        {filteredInstruments.length === 0 ? (
          <EmptyState
            id="cf-markets-empty-state"
            icon="search"
            title="No Matching Instruments"
            description={
              localSearch || selectedCategory !== 'all'
                ? `No instruments matched "${localSearch}" in category "${selectedCategory}".`
                : 'No market instruments are currently available.'
            }
            action={
              localSearch || selectedCategory !== 'all'
                ? {
                    label: 'Reset Filters',
                    onClick: () => {
                      setLocalSearch('')
                      setSelectedCategory('all')
                    },
                    id: 'cf-reset-filters-btn',
                  }
                : null
            }
          />
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
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {filteredInstruments.map((inst) => (
                  <tr
                    key={inst.symbol}
                    id={`market-inst-${inst.symbol}`}
                    onClick={() => handleOpenDetail(inst)}
                    style={{
                      borderBottom: '1px solid var(--cf-border)',
                      transition: 'background var(--cf-transition-fast)',
                      cursor: 'pointer',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td style={{ padding: '14px 16px', fontWeight: 700, color: 'var(--cf-brand-cyan)' }}>
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
                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <button
                        id={`btn-chart-${inst.symbol}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleOpenDetail(inst)
                        }}
                        style={{
                          background: 'rgba(6, 182, 212, 0.12)',
                          color: 'var(--cf-brand-cyan)',
                          border: '1px solid rgba(6, 182, 212, 0.25)',
                          borderRadius: 'var(--cf-radius-sm)',
                          padding: '4px 10px',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Chart
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Central Asset Detail Experience Modal */}
      {selectedInstrument && (
        <AssetDetailModal
          instrument={selectedInstrument}
          quote={quoteDetail}
          chartBars={chartBars}
          indicators={indicatorsData}
          intelligence={intelligenceDetail}
          returnsAnalysis={returnsData}
          isLoading={isChartLoading || isIntelligenceLoading}
          chartTimeframe={chartTimeframe}
          onTimeframeChange={(tf) => setChartTimeframe(tf)}
          onClose={handleCloseDetail}
          onPersistQuote={handlePersistQuote}
          onBackfillBars={handleBackfillBars}
          actionFeedback={actionFeedback}
          isInWatchlist={isInWatchlist}
          onToggleWatchlist={handleToggleWatchlist}
        />
      )}
    </div>
  )
}
