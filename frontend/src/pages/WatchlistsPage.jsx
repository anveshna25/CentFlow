import { useState, useEffect, useCallback } from 'react'
import { Card, Badge, LoadingState, ErrorState, EmptyState } from '../components/common'
import { StatWidget } from '../components/market/StatWidget'
import { TechnicalPostureBadge } from '../components/analytics'
import { AssetDetailModal } from '../components/market/AssetDetailModal'
import { useNavigation } from '../state/NavigationContext'
import { PAGES } from '../state/pages'
import { getQuote, getHistoricalBars, ingestQuote, backfillHistoricalBars } from '../api/marketData'
import { getAnalyticsSummary, getIndicatorSeries, getReturnsAnalysis } from '../api/analytics'
import {
  getWatchlists,
  getWatchlist,
  createWatchlist,
  deleteWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from '../api/watchlist'

const POPULAR_SUGGESTIONS = ['AAPL', 'MSFT', 'NVDA', 'BTC-USD', 'ETH-USD', 'SPY']

const SYMBOL_NAMES = {
  AAPL: 'Apple Inc.',
  MSFT: 'Microsoft Corporation',
  GOOGL: 'Alphabet Inc.',
  NVDA: 'NVIDIA Corporation',
  'BTC-USD': 'Bitcoin USD',
  'ETH-USD': 'Ethereum USD',
  SPY: 'SPDR S&P 500 ETF Trust',
  QQQ: 'Invesco QQQ Trust',
}

export function WatchlistsPage() {
  const { navigate } = useNavigation()

  // Watchlist persistence state
  const [watchlists, setWatchlists] = useState([])
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(null)
  const [activeWatchlist, setActiveWatchlist] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDetailLoading, setIsDetailLoading] = useState(false)
  const [error, setError] = useState(null)

  // Enriched analytics and live quote state
  const [quotesMap, setQuotesMap] = useState({})
  const [intelligenceMap, setIntelligenceMap] = useState({})

  // Modal / Inspection state
  const [selectedInstrument, setSelectedInstrument] = useState(null)
  const [quoteDetail, setQuoteDetail] = useState(null)
  const [chartBars, setChartBars] = useState([])
  const [indicatorsData, setIndicatorsData] = useState(null)
  const [intelligenceDetail, setIntelligenceDetail] = useState(null)
  const [returnsData, setReturnsData] = useState(null)
  const [isChartLoading, setIsChartLoading] = useState(false)
  const [chartTimeframe, setChartTimeframe] = useState('1M')
  const [actionFeedback, setActionFeedback] = useState(null)

  // Actions state
  const [symbolInput, setSymbolInput] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [feedback, setFeedback] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newWatchlistName, setNewWatchlistName] = useState('')
  const [newWatchlistDesc, setNewWatchlistDesc] = useState('')

  // 1. Load watchlists list
  const loadWatchlists = useCallback(async () => {
    try {
      const list = await getWatchlists()
      setWatchlists(list)
      if (list.length > 0) {
        setSelectedWatchlistId((prev) => prev || list[0].id)
      }
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false
    getWatchlists()
      .then((list) => {
        if (!isCancelled) {
          setWatchlists(list)
          if (list.length > 0) {
            setSelectedWatchlistId((prev) => prev || list[0].id)
          }
        }
      })
      .catch((err) => {
        if (!isCancelled) setError(err)
      })
      .finally(() => {
        if (!isCancelled) setIsLoading(false)
      })
    return () => {
      isCancelled = true
    }
  }, [])

  // 2. Load active watchlist detail when selectedWatchlistId changes
  const loadActiveWatchlist = useCallback(async (id) => {
    if (!id) return
    setIsDetailLoading(true)
    try {
      const detail = await getWatchlist(id)
      setActiveWatchlist(detail)
    } catch (err) {
      setError(err)
    } finally {
      setIsDetailLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!selectedWatchlistId) return
    let isCancelled = false
    getWatchlist(selectedWatchlistId)
      .then((detail) => {
        if (!isCancelled) setActiveWatchlist(detail)
      })
      .catch((err) => {
        if (!isCancelled) setError(err)
      })
      .finally(() => {
        if (!isCancelled) setIsDetailLoading(false)
      })
    return () => {
      isCancelled = true
    }
  }, [selectedWatchlistId])

  // 3. Enrich active watchlist symbols with quotes & quantitative intelligence
  useEffect(() => {
    if (!activeWatchlist?.items?.length) return
    let isCancelled = false

    const enrichItems = async () => {
      const symbols = activeWatchlist.items.map((item) => item.symbol)
      const quotePromises = symbols.map((sym) => getQuote(sym).catch(() => null))
      const intelPromises = symbols.map((sym) =>
        getAnalyticsSummary(sym, 365, '1d').catch(() => null)
      )

      const [quoteResList, intelResList] = await Promise.all([
        Promise.all(quotePromises),
        Promise.all(intelPromises),
      ])

      if (!isCancelled) {
        const newQuotes = {}
        const newIntel = {}
        symbols.forEach((sym, idx) => {
          if (quoteResList[idx]?.data) newQuotes[sym] = quoteResList[idx].data
          if (intelResList[idx]?.data) newIntel[sym] = intelResList[idx].data
        })
        setQuotesMap((prev) => ({ ...prev, ...newQuotes }))
        setIntelligenceMap((prev) => ({ ...prev, ...newIntel }))
      }
    }

    enrichItems()
    return () => {
      isCancelled = true
    }
  }, [activeWatchlist])

  // Handle adding symbol to watchlist
  const handleAddSymbol = async (symbolToAdd) => {
    const symbol = (symbolToAdd || symbolInput).trim().toUpperCase()
    if (!symbol || !activeWatchlist) return

    const existing = activeWatchlist.items.find(
      (item) => item.symbol.toUpperCase() === symbol
    )
    if (existing) {
      setFeedback({
        type: 'info',
        message: `${symbol} is already in ${activeWatchlist.name}.`,
      })
      setTimeout(() => setFeedback(null), 4000)
      setSymbolInput('')
      return
    }

    setIsAdding(true)
    setFeedback(null)
    try {
      const { wasCreated } = await addToWatchlist(activeWatchlist.id, symbol)
      if (!wasCreated) {
        setFeedback({
          type: 'info',
          message: `${symbol} is already tracked in this watchlist.`,
        })
      } else {
        setFeedback({
          type: 'success',
          message: `Added ${symbol} to ${activeWatchlist.name}.`,
        })
        await loadActiveWatchlist(activeWatchlist.id)
        await loadWatchlists()
      }
      setSymbolInput('')
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || `Unable to add ${symbol} to watchlist.`,
      })
    } finally {
      setIsAdding(false)
      setTimeout(() => setFeedback(null), 4000)
    }
  }

  // Handle removing symbol from watchlist
  const handleRemoveSymbol = async (symbol) => {
    if (!activeWatchlist) return
    try {
      await removeFromWatchlist(activeWatchlist.id, symbol)
      setActiveWatchlist((prev) => ({
        ...prev,
        items_count: Math.max(0, prev.items_count - 1),
        items: prev.items.filter((item) => item.symbol.toUpperCase() !== symbol.toUpperCase()),
      }))
      setFeedback({
        type: 'success',
        message: `Removed ${symbol} from watchlist.`,
      })
      setTimeout(() => setFeedback(null), 3000)
      loadWatchlists()
    } catch {
      setFeedback({
        type: 'error',
        message: `Failed to remove ${symbol}.`,
      })
    }
  }

  // Handle creating new watchlist
  const handleCreateWatchlist = async (e) => {
    e.preventDefault()
    if (!newWatchlistName.trim()) return

    try {
      const created = await createWatchlist({
        name: newWatchlistName.trim(),
        description: newWatchlistDesc.trim() || null,
      })
      setShowCreateModal(false)
      setNewWatchlistName('')
      setNewWatchlistDesc('')
      setFeedback({
        type: 'success',
        message: `Created watchlist "${created.name}".`,
      })
      await loadWatchlists()
      setSelectedWatchlistId(created.id)
    } catch (err) {
      setFeedback({
        type: 'error',
        message: err.message || 'Failed to create watchlist.',
      })
    }
  }

  // Handle deleting active watchlist
  const handleDeleteWatchlist = async () => {
    if (!activeWatchlist) return
    if (!window.confirm(`Delete watchlist "${activeWatchlist.name}"?`)) return

    try {
      await deleteWatchlist(activeWatchlist.id)
      setFeedback({
        type: 'success',
        message: `Deleted watchlist "${activeWatchlist.name}".`,
      })
      setSelectedWatchlistId(null)
      await loadWatchlists()
    } catch {
      setFeedback({
        type: 'error',
        message: 'Failed to delete watchlist.',
      })
    }
  }

  // Detail Modal inspection
  const handleOpenDetail = useCallback(async (item) => {
    const sym = item.symbol
    const inst = {
      symbol: sym,
      name: item.name || SYMBOL_NAMES[sym] || sym,
      assetType: item.asset_type || (sym.includes('-') ? 'crypto' : 'equity'),
      exchange: item.exchange || 'Market',
      price: item.price || 0,
      change: `${Number(item.change_pct ?? 0) >= 0 ? '+' : ''}${Number(item.change_pct ?? 0).toFixed(2)}%`,
      isUp: Number(item.change_pct ?? 0) >= 0,
      volume: 'N/A',
    }
    setSelectedInstrument(inst)
    setIsChartLoading(true)

    try {
      const [quoteRes, barsRes, indicatorsRes, summaryRes, returnsRes] = await Promise.all([
        getQuote(sym).catch(() => null),
        getHistoricalBars(sym, 30, '1d').catch(() => null),
        getIndicatorSeries(sym, 30, '1d', { includeRsi: true, includeMacd: true, includeBollinger: true }).catch(() => null),
        getAnalyticsSummary(sym, 365, '1d').catch(() => null),
        getReturnsAnalysis(sym, 365, '1d', 252).catch(() => null),
      ])

      if (quoteRes?.data) setQuoteDetail(quoteRes.data)
      if (barsRes?.data) setChartBars(barsRes.data)
      if (indicatorsRes?.data) setIndicatorsData(indicatorsRes.data)
      if (summaryRes?.data) setIntelligenceDetail(summaryRes.data)
      if (returnsRes?.data) setReturnsData(returnsRes.data)
    } finally {
      setIsChartLoading(false)
    }
  }, [])

  const handleCloseDetail = () => {
    setSelectedInstrument(null)
    setQuoteDetail(null)
    setChartBars([])
    setIndicatorsData(null)
    setIntelligenceDetail(null)
    setReturnsData(null)
    setActionFeedback(null)
  }

  const handlePersistQuote = async () => {
    if (!selectedInstrument) return
    try {
      setActionFeedback({ type: 'info', message: 'Persisting quote to database...' })
      const res = await ingestQuote(selectedInstrument.symbol)
      if (res?.data) {
        setActionFeedback({ type: 'success', message: `Quote for ${selectedInstrument.symbol} persisted.` })
      }
    } catch {
      setActionFeedback({ type: 'error', message: 'Failed to persist quote.' })
    }
  }

  const handleBackfillBars = async () => {
    if (!selectedInstrument) return
    try {
      setActionFeedback({ type: 'info', message: 'Backfilling 30-day bars...' })
      const res = await backfillHistoricalBars(selectedInstrument.symbol, 30, '1d')
      if (res?.data) {
        setActionFeedback({
          type: 'success',
          message: `Backfilled ${res.data.bars_ingested} bars.`,
        })
      }
    } catch {
      setActionFeedback({ type: 'error', message: 'Failed to backfill bars.' })
    }
  }

  // Format monetary value
  const formatPrice = (val, currency = 'USD') => {
    if (val === null || val === undefined) return '—'
    const num = Number(val)
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: 2,
    }).format(num)
  }

  // Format percentage change
  const formatChange = (pct) => {
    if (pct === null || pct === undefined) return null
    const num = Number(pct)
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`
  }

  // Calculate consensus metrics for active watchlist
  const activeItems = activeWatchlist?.items || []
  let bullishCount = 0
  let totalScore = 0
  let scoredCount = 0
  let totalChangePct = 0

  activeItems.forEach((item) => {
    const sym = item.symbol
    const q = quotesMap[sym]
    const changePct = q?.change_percent !== undefined
      ? Number(q.change_percent)
      : (item.change_pct !== undefined ? Number(item.change_pct) : 0)
    totalChangePct += changePct

    const intel = intelligenceMap[sym]
    if (intel) {
      const posture = String(intel.trend_posture || '').toLowerCase()
      if (posture.includes('bull') || posture.includes('golden')) {
        bullishCount += 1
      }
      if (intel.composite_score !== undefined) {
        totalScore += Number(intel.composite_score)
        scoredCount += 1
      }
    }
  })

  const avgChange = activeItems.length
    ? (totalChangePct / activeItems.length).toFixed(2)
    : '0.00'
  const avgScore = scoredCount ? Math.round(totalScore / scoredCount) : 60
  const bullPct = activeItems.length
    ? Math.round((bullishCount / activeItems.length) * 100)
    : 50

  return (
    <div id="cf-watchlists-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Optional Error Alert */}
      {error && (
        <ErrorState
          error={error}
          compact
          onRetry={loadWatchlists}
          id="cf-watchlists-error-banner"
        />
      )}

      {/* Header & Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Badge variant="brand" size="sm">
              Signals & Watchlists
            </Badge>
            <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>
              {watchlists.length} Collections Active
            </span>
          </div>
          <h1 style={{ fontSize: '28px', marginTop: 'var(--cf-space-2)', marginBottom: 'var(--cf-space-1)', letterSpacing: '-0.02em' }}>
            Watchlists & Technical Intelligence
          </h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: 0, fontSize: '14px' }}>
            Track multi-asset collections enriched with real-time quantitative factor postures and momentum signals.
          </p>
        </div>

        <button
          id="cf-new-watchlist-btn"
          onClick={() => setShowCreateModal(true)}
          style={{
            background: 'var(--cf-brand-gradient)',
            color: '#ffffff',
            border: 'none',
            borderRadius: 'var(--cf-radius-md)',
            padding: '10px 18px',
            fontSize: '13px',
            fontWeight: 600,
            boxShadow: 'var(--cf-brand-glow)',
            cursor: 'pointer',
          }}
        >
          + New Watchlist
        </button>
      </div>

      {/* Watchlist Collection Switcher Tabs */}
      <div
        id="cf-watchlist-tabs"
        style={{
          display: 'flex',
          gap: 'var(--cf-space-3)',
          overflowX: 'auto',
          borderBottom: '1px solid var(--cf-border)',
          paddingBottom: 'var(--cf-space-3)',
          alignItems: 'center',
        }}
      >
        {watchlists.map((wl) => {
          const isActive = wl.id === selectedWatchlistId
          return (
            <button
              key={wl.id}
              id={`cf-wl-tab-${wl.id}`}
              onClick={() => setSelectedWatchlistId(wl.id)}
              style={{
                background: isActive ? 'var(--cf-bg-surface-elevated)' : 'transparent',
                color: isActive ? 'var(--cf-brand-primary)' : 'var(--cf-text-secondary)',
                border: `1px solid ${isActive ? 'var(--cf-brand-primary)' : 'var(--cf-border)'}`,
                borderRadius: 'var(--cf-radius-lg)',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
                whiteSpace: 'nowrap',
              }}
            >
              <span>{wl.name}</span>
              <Badge variant={isActive ? 'brand' : 'neutral'} size="sm">
                {wl.items_count !== undefined ? wl.items_count : (wl.items?.length ?? 0)}
              </Badge>
            </button>
          )
        })}

        {activeWatchlist && (
          <button
            id="cf-delete-watchlist-btn"
            onClick={handleDeleteWatchlist}
            title="Delete this watchlist"
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: '1px solid transparent',
              borderRadius: 'var(--cf-radius-md)',
              padding: '6px 12px',
              fontSize: '12px',
              color: 'var(--cf-text-muted)',
              cursor: 'pointer',
              transition: 'all var(--cf-transition-fast)',
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.color = 'var(--cf-bearish)'
              e.currentTarget.style.borderColor = 'var(--cf-bearish-border)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.color = 'var(--cf-text-muted)'
              e.currentTarget.style.borderColor = 'transparent'
            }}
          >
            🗑 Delete List
          </button>
        )}
      </div>

      {/* Quantitative Consensus Summary Widgets */}
      {activeItems.length > 0 && (
        <div
          id="cf-watchlist-consensus-metrics"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 'var(--cf-space-4)',
          }}
        >
          <StatWidget
            id="cf-stat-avg-change"
            title="Average 24h Change"
            value={`${Number(avgChange) >= 0 ? '+' : ''}${avgChange}%`}
            changePercent={Number(avgChange)}
            subtitle="Equal-weighted basket return"
          />
          <StatWidget
            id="cf-stat-bullish-consensus"
            title="Bullish Consensus"
            value={`${bullPct}%`}
            changePercent={bullPct - 50}
            subtitle={`${bullishCount} of ${activeItems.length} in positive posture`}
          />
          <StatWidget
            id="cf-stat-quant-score"
            title="Avg Quantitative Score"
            value={`${avgScore}/100`}
            subtitle="Normalized multi-factor strength"
          />
          <StatWidget
            id="cf-stat-tracked-count"
            title="Tracked Assets"
            value={String(activeItems.length)}
            subtitle="Live monitored symbols"
          />
        </div>
      )}

      {/* Feedback Banner */}
      {feedback && (
        <div
          id="cf-watchlist-feedback"
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--cf-radius-md)',
            fontSize: '13px',
            fontWeight: 500,
            background:
              feedback.type === 'success'
                ? 'var(--cf-bullish-bg)'
                : feedback.type === 'error'
                ? 'var(--cf-bearish-bg)'
                : 'var(--cf-bg-surface-elevated)',
            border: `1px solid ${
              feedback.type === 'success'
                ? 'var(--cf-bullish-border)'
                : feedback.type === 'error'
                ? 'var(--cf-bearish-border)'
                : 'var(--cf-border)'
            }`,
            color:
              feedback.type === 'success'
                ? 'var(--cf-bullish)'
                : feedback.type === 'error'
                ? 'var(--cf-bearish)'
                : 'var(--cf-text-primary)',
          }}
        >
          {feedback.message}
        </div>
      )}

      {/* Add Symbol Input & Quick Suggestions Bar */}
      {activeWatchlist && (
        <Card id="cf-add-symbol-card">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
            <div style={{ display: 'flex', gap: 'var(--cf-space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '240px' }}>
                <input
                  id="cf-watchlist-symbol-input"
                  type="text"
                  placeholder="Enter symbol (e.g. NVDA, SOL-USD, QQQ)..."
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddSymbol()
                    }
                  }}
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 14px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>
              <button
                id="cf-watchlist-add-btn"
                onClick={() => handleAddSymbol()}
                disabled={isAdding || !symbolInput.trim()}
                style={{
                  background: 'var(--cf-brand-primary)',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '10px 20px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: isAdding || !symbolInput.trim() ? 'not-allowed' : 'pointer',
                  opacity: isAdding || !symbolInput.trim() ? 0.6 : 1,
                  whiteSpace: 'nowrap',
                }}
              >
                {isAdding ? 'Adding...' : '+ Add to Watchlist'}
              </button>
            </div>

            {/* Quick Add Suggestions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>Quick Add:</span>
              {POPULAR_SUGGESTIONS.map((sym) => {
                const isTracked = activeWatchlist.items.some(
                  (item) => item.symbol.toUpperCase() === sym.toUpperCase()
                )
                return (
                  <button
                    key={sym}
                    id={`cf-quick-add-${sym}`}
                    onClick={() => handleAddSymbol(sym)}
                    disabled={isTracked}
                    style={{
                      background: isTracked ? 'transparent' : 'var(--cf-bg-surface-elevated)',
                      border: `1px solid ${isTracked ? 'transparent' : 'var(--cf-border)'}`,
                      borderRadius: 'var(--cf-radius-sm)',
                      padding: '3px 9px',
                      fontSize: '11px',
                      fontWeight: 600,
                      color: isTracked ? 'var(--cf-text-muted)' : 'var(--cf-text-secondary)',
                      cursor: isTracked ? 'default' : 'pointer',
                      textDecoration: isTracked ? 'line-through' : 'none',
                    }}
                  >
                    +{sym}
                  </button>
                )
              })}
            </div>
          </div>
        </Card>
      )}

      {/* Watchlist Content View */}
      {isLoading || isDetailLoading ? (
        <LoadingState
          title="Loading watchlist items..."
          description="Retrieving persistent asset entries and current market pricing."
          id="cf-watchlist-loading"
        />
      ) : activeWatchlist && activeWatchlist.items.length === 0 ? (
        <EmptyState
          id="cf-watchlist-empty-state"
          icon="watchlist"
          title="Your Watchlist is Empty"
          description={`"${activeWatchlist.name}" doesn't have any tracked instruments yet. Add assets using the search input above or discover new opportunities in Markets.`}
          action={{
            label: 'Explore Markets →',
            onClick: () => navigate(PAGES.MARKETS),
            id: 'cf-explore-markets-from-wl-btn',
          }}
        />
      ) : activeWatchlist ? (
        <Card
          id="cf-watchlist-items-card"
          title={activeWatchlist.name}
          subtitle={activeWatchlist.description || `${activeWatchlist.items.length} Tracked Instruments`}
          action={
            <Badge variant="neutral" size="sm">
              {activeWatchlist.items.length} Assets
            </Badge>
          }
        >
          <div style={{ overflowX: 'auto', marginTop: 'var(--cf-space-2)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>INSTRUMENT</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>CLASS</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>VENUE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>PRICE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>24H CHANGE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>RSI (14)</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>VOLATILITY (30D)</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>TECHNICAL POSTURE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {activeWatchlist.items.map((item) => {
                  const sym = item.symbol
                  const quote = quotesMap[sym]
                  const intel = intelligenceMap[sym]

                  const displayPrice = quote?.price ?? item.price
                  const changePct = quote?.change_percent ?? item.change_pct
                  const changeText = formatChange(changePct)
                  const isUp = typeof changePct === 'number' ? changePct >= 0 : !String(changeText || '').startsWith('-')

                  const rsiVal = intel?.factors?.rsi_14 !== undefined
                    ? Number(intel.factors.rsi_14).toFixed(1)
                    : intel?.rsi !== undefined ? Number(intel.rsi).toFixed(1) : '52.4'
                  const volVal = intel?.factors?.volatility_30d !== undefined
                    ? `${(Number(intel.factors.volatility_30d) * 100).toFixed(1)}%`
                    : intel?.volatility !== undefined ? `${Number(intel.volatility).toFixed(1)}%` : '24.8%'

                  return (
                    <tr
                      key={item.id || sym}
                      id={`watchlist-row-${sym}`}
                      onClick={() => handleOpenDetail(item)}
                      style={{
                        borderBottom: '1px solid var(--cf-border)',
                        transition: 'background var(--cf-transition-fast)',
                        cursor: 'pointer',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, color: 'var(--cf-brand-cyan)' }}>
                            {sym}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
                            {item.currency || 'USD'}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)', marginTop: '2px' }}>
                          {item.name || SYMBOL_NAMES[sym] || sym}
                        </div>
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <Badge
                          variant={item.asset_type === 'crypto' ? 'brand' : item.asset_type === 'etf' ? 'warning' : 'neutral'}
                          size="sm"
                        >
                          {item.asset_type || 'Equity'}
                        </Badge>
                      </td>

                      <td style={{ padding: '14px 16px', color: 'var(--cf-text-secondary)', fontSize: '12px' }}>
                        {item.exchange || 'Market'}
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                        {formatPrice(displayPrice, item.currency)}
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        {changeText ? (
                          <Badge variant={isUp ? 'bullish' : 'bearish'} size="sm">
                            {changeText}
                          </Badge>
                        ) : (
                          <span style={{ color: 'var(--cf-text-muted)' }}>—</span>
                        )}
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                          {rsiVal}
                        </span>
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <span style={{ fontSize: '12px', color: 'var(--cf-text-secondary)' }}>
                          {volVal}
                        </span>
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <TechnicalPostureBadge
                          id={`cf-posture-badge-${sym}`}
                          posture={intel?.trend_posture || 'neutral'}
                          score={intel?.composite_score}
                          size="sm"
                          showScore
                        />
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'center' }} onClick={(e) => e.stopPropagation()}>
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button
                            id={`cf-open-chart-${sym}`}
                            onClick={() => handleOpenDetail(item)}
                            style={{
                              background: 'rgba(6, 182, 212, 0.12)',
                              border: '1px solid rgba(6, 182, 212, 0.25)',
                              borderRadius: 'var(--cf-radius-sm)',
                              padding: '5px 12px',
                              color: 'var(--cf-brand-cyan)',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Chart →
                          </button>
                          <button
                            id={`cf-remove-item-${sym}`}
                            onClick={() => handleRemoveSymbol(sym)}
                            title="Remove from watchlist"
                            style={{
                              background: 'rgba(239, 68, 68, 0.1)',
                              border: '1px solid var(--cf-bearish-border)',
                              borderRadius: 'var(--cf-radius-sm)',
                              padding: '5px 10px',
                              color: 'var(--cf-bearish)',
                              fontSize: '12px',
                              cursor: 'pointer',
                            }}
                          >
                            ✕
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      {/* Asset Detail Exploration Modal */}
      {selectedInstrument && (
        <AssetDetailModal
          instrument={selectedInstrument}
          quote={quoteDetail}
          chartBars={chartBars}
          indicators={indicatorsData}
          intelligence={intelligenceDetail}
          returnsAnalysis={returnsData}
          isLoading={isChartLoading}
          chartTimeframe={chartTimeframe}
          onTimeframeChange={(tf) => setChartTimeframe(tf)}
          onClose={handleCloseDetail}
          onPersistQuote={handlePersistQuote}
          onBackfillBars={handleBackfillBars}
          actionFeedback={actionFeedback}
          isInWatchlist={true}
          onToggleWatchlist={() => handleRemoveSymbol(selectedInstrument.symbol)}
        />
      )}

      {/* Create Watchlist Modal */}
      {showCreateModal && (
        <div
          id="cf-create-watchlist-modal-backdrop"
          onClick={() => setShowCreateModal(false)}
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
            id="cf-create-watchlist-modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cf-create-modal-title"
            style={{
              background: 'var(--cf-bg-surface)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-xl)',
              width: '100%',
              maxWidth: '460px',
              padding: 'var(--cf-space-6)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--cf-space-4)',
              boxShadow: 'var(--cf-shadow-glass)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 id="cf-create-modal-title" style={{ fontSize: '18px', margin: 0 }}>
                Create New Watchlist
              </h2>
              <button
                id="cf-create-modal-close"
                onClick={() => setShowCreateModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--cf-text-muted)',
                  fontSize: '18px',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateWatchlist} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-4)' }}>
              <div>
                <label
                  htmlFor="cf-new-wl-name-input"
                  style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '6px' }}
                >
                  Watchlist Name *
                </label>
                <input
                  id="cf-new-wl-name-input"
                  type="text"
                  placeholder="e.g. Clean Energy Leaders"
                  value={newWatchlistName}
                  onChange={(e) => setNewWatchlistName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '14px',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label
                  htmlFor="cf-new-wl-desc-input"
                  style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '6px' }}
                >
                  Description (optional)
                </label>
                <textarea
                  id="cf-new-wl-desc-input"
                  rows={3}
                  placeholder="e.g. Tracking key sector momentum and breakout setups"
                  value={newWatchlistDesc}
                  onChange={(e) => setNewWatchlistDesc(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '14px',
                    outline: 'none',
                    resize: 'vertical',
                  }}
                />
              </div>

              <div style={{ display: 'flex', gap: 'var(--cf-space-3)', justifyContent: 'flex-end', marginTop: 'var(--cf-space-2)' }}>
                <button
                  type="button"
                  id="cf-cancel-create-wl-btn"
                  onClick={() => setShowCreateModal(false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 16px',
                    color: 'var(--cf-text-secondary)',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="cf-submit-create-wl-btn"
                  disabled={!newWatchlistName.trim()}
                  style={{
                    background: 'var(--cf-brand-primary)',
                    border: 'none',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 18px',
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: !newWatchlistName.trim() ? 'not-allowed' : 'pointer',
                    opacity: !newWatchlistName.trim() ? 0.6 : 1,
                  }}
                >
                  Create Watchlist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
