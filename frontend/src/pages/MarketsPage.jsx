import { useState, useEffect, useCallback, useTransition } from 'react'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { PriceChart } from '../components/market/PriceChart'
import {
  searchInstruments,
  getQuote,
  getHistoricalBars,
  ingestQuote,
  backfillHistoricalBars,
} from '../api/marketData'

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
  const [, startTransition] = useTransition()
  const [instruments, setInstruments] = useState(DEFAULT_INSTRUMENTS)
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [localSearch, setLocalSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Selected Instrument Detail & Chart State
  const [selectedInstrument, setSelectedInstrument] = useState(null)
  const [quoteDetail, setQuoteDetail] = useState(null)
  const [chartBars, setChartBars] = useState([])
  const [chartTimeframe, setChartTimeframe] = useState('1M')
  const [isChartLoading, setIsChartLoading] = useState(false)
  const [actionFeedback, setActionFeedback] = useState(null)

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

  // Load historical bars and quote details when selecting an instrument
  useEffect(() => {
    if (!selectedInstrument) return
    let isCancelled = false

    const fetchChartData = async () => {
      setIsChartLoading(true)
      const config = TIMEFRAME_CONFIG[chartTimeframe] || TIMEFRAME_CONFIG['1M']
      try {
        const [barsRes, quoteRes] = await Promise.all([
          getHistoricalBars(selectedInstrument.symbol, config.days, config.interval).catch(() => null),
          getQuote(selectedInstrument.symbol).catch(() => null),
        ])

        if (!isCancelled) {
          if (barsRes?.data) {
            setChartBars(barsRes.data)
          }
          if (quoteRes?.data) {
            setQuoteDetail(quoteRes.data)
          }
        }
      } finally {
        if (!isCancelled) {
          setIsChartLoading(false)
        }
      }
    }

    fetchChartData()
    return () => {
      isCancelled = true
    }
  }, [selectedInstrument, chartTimeframe])

  const handleOpenDetail = (inst) => {
    startTransition(() => {
      setSelectedInstrument(inst)
      setActionFeedback(null)
    })
  }

  const handleCloseDetail = () => {
    setSelectedInstrument(null)
    setQuoteDetail(null)
    setChartBars([])
    setActionFeedback(null)
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
          message: `Backfilled ${res.data.bars_ingested} bars for ${selectedInstrument.symbol}.`,
        })
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
        <ErrorBanner
          error={error}
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
        <LoadingSpinner message="Retrieving instruments and quotes from backend..." id="cf-markets-spinner" />
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
          <div style={{ padding: 'var(--cf-space-8)', textAlign: 'center', color: 'var(--cf-text-muted)' }}>
            No instruments match the current filter or search criteria.
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

      {/* Interactive Chart & Instrument Detail Modal */}
      {selectedInstrument && (
        <div
          id="cf-chart-modal-backdrop"
          onClick={handleCloseDetail}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(6px)',
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 'var(--cf-space-4)',
          }}
        >
          <div
            id="cf-chart-modal-content"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cf-chart-modal-title"
            style={{
              background: 'var(--cf-bg-surface)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-xl)',
              width: '100%',
              maxWidth: '920px',
              maxHeight: '92vh',
              overflowY: 'auto',
              boxShadow: 'var(--cf-shadow-glass)',
              padding: 'var(--cf-space-6)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--cf-space-5)',
            }}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <h2 id="cf-chart-modal-title" style={{ fontSize: '22px', margin: 0, letterSpacing: '-0.02em' }}>
                    {selectedInstrument.symbol}
                  </h2>
                  <Badge variant="brand" size="sm">
                    {selectedInstrument.assetType}
                  </Badge>
                  <span style={{ color: 'var(--cf-text-muted)', fontSize: '12px' }}>
                    {selectedInstrument.exchange}
                  </span>
                </div>
                <div style={{ color: 'var(--cf-text-secondary)', fontSize: '14px', marginTop: '2px' }}>
                  {selectedInstrument.name}
                </div>
              </div>

              {/* Close Button */}
              <button
                id="cf-chart-modal-close"
                onClick={handleCloseDetail}
                style={{
                  background: 'var(--cf-bg-surface-elevated)',
                  border: '1px solid var(--cf-border)',
                  color: 'var(--cf-text-secondary)',
                  borderRadius: 'var(--cf-radius-full)',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '16px',
                }}
              >
                ✕
              </button>
            </div>

            {/* Quote Key Statistics Grid */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: 'var(--cf-space-3)',
                background: 'var(--cf-bg-base)',
                padding: 'var(--cf-space-4)',
                borderRadius: 'var(--cf-radius-lg)',
                border: '1px solid var(--cf-border)',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Price</div>
                <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                  ${Number(quoteDetail?.price ?? selectedInstrument.price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>24h Change</div>
                <div
                  style={{
                    fontSize: '16px',
                    fontWeight: 700,
                    color: selectedInstrument.isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)',
                  }}
                >
                  {selectedInstrument.change}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Open</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                  {quoteDetail?.open ? `$${Number(quoteDetail.open).toFixed(2)}` : 'N/A'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>24h High</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--cf-bullish)' }}>
                  {quoteDetail?.high ? `$${Number(quoteDetail.high).toFixed(2)}` : 'N/A'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>24h Low</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--cf-bearish)' }}>
                  {quoteDetail?.low ? `$${Number(quoteDetail.low).toFixed(2)}` : 'N/A'}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Volume</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--cf-text-secondary)' }}>
                  {selectedInstrument.volume}
                </div>
              </div>
            </div>

            {/* Interactive Price Chart */}
            <PriceChart
              id={`modal-chart-${selectedInstrument.symbol}`}
              data={chartBars}
              symbol={selectedInstrument.symbol}
              currency="USD"
              isLoading={isChartLoading}
              timeframe={chartTimeframe}
              onTimeframeChange={(tf) => setChartTimeframe(tf)}
              height={340}
            />

            {/* Ingestion & Persistence Actions */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 'var(--cf-space-3)',
                borderTop: '1px solid var(--cf-border)',
                paddingTop: 'var(--cf-space-3)',
              }}
            >
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <button
                  id="btn-persist-quote"
                  onClick={handlePersistQuote}
                  style={{
                    background: 'var(--cf-bg-surface-elevated)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    color: 'var(--cf-text-primary)',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all var(--cf-transition-fast)',
                  }}
                >
                  Persist Quote Observation
                </button>
                <button
                  id="btn-backfill-bars"
                  onClick={handleBackfillBars}
                  style={{
                    background: 'var(--cf-bg-surface-elevated)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    color: 'var(--cf-brand-cyan)',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all var(--cf-transition-fast)',
                  }}
                >
                  Backfill 30-Day History
                </button>
              </div>

              {actionFeedback && (
                <div
                  id="cf-action-feedback"
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color:
                      actionFeedback.type === 'success'
                        ? 'var(--cf-bullish)'
                        : actionFeedback.type === 'error'
                        ? 'var(--cf-bearish)'
                        : 'var(--cf-brand-cyan)',
                  }}
                >
                  {actionFeedback.message}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
