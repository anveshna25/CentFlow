import { useState, useEffect, useCallback } from 'react'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { StatWidget } from '../components/market/StatWidget'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { TechnicalPostureBadge } from '../components/analytics'
import { AssetDetailModal } from '../components/market/AssetDetailModal'
import { getQuote } from '../api/marketData'
import { getAnalyticsSummary } from '../api/analytics'

const INITIAL_WATCHLISTS = [
  {
    id: 'wl-tech',
    name: 'Mega-Cap Technology',
    description: 'High-conviction core enterprise technology and cloud leaders',
    symbols: ['AAPL', 'MSFT', 'GOOGL', 'NVDA'],
    category: 'equity',
  },
  {
    id: 'wl-crypto',
    name: 'Decentralized Layer 1s',
    description: 'Dominant smart contract platforms and decentralized monetary assets',
    symbols: ['BTC-USD', 'ETH-USD'],
    category: 'crypto',
  },
  {
    id: 'wl-macro',
    name: 'Macro & Index Hedges',
    description: 'Broad equity benchmarks and liquid ETF macroeconomic proxies',
    symbols: ['SPY', 'QQQ'],
    category: 'etf',
  },
]

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
  const [watchlists, setWatchlists] = useState(INITIAL_WATCHLISTS)
  const [activeWatchlistId, setActiveWatchlistId] = useState(INITIAL_WATCHLISTS[0].id)
  const [quotesMap, setQuotesMap] = useState({})
  const [intelligenceMap, setIntelligenceMap] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  // Inspection modal state
  const [selectedSymbol, setSelectedSymbol] = useState(null)

  // New Watchlist modal state
  const [isNewWlOpen, setIsNewWlOpen] = useState(false)
  const [newWlName, setNewWlName] = useState('')
  const [newWlDesc, setNewWlDesc] = useState('')
  const [newWlSymbols, setNewWlSymbols] = useState('')

  const activeWatchlist =
    watchlists.find((wl) => wl.id === activeWatchlistId) || watchlists[0]

  // Fetch quotes and analytics summaries for symbols in active watchlist
  const loadWatchlistData = useCallback(async () => {
    if (!activeWatchlist?.symbols?.length) return
    setError(null)
    setIsLoading(true)

    try {
      const symbols = activeWatchlist.symbols
      const quotePromises = symbols.map((sym) => getQuote(sym).catch(() => null))
      const intelPromises = symbols.map((sym) =>
        getAnalyticsSummary(sym, 365, '1d').catch(() => null)
      )

      const [quoteResponses, intelResponses] = await Promise.all([
        Promise.all(quotePromises),
        Promise.all(intelPromises),
      ])

      const newQuotes = {}
      const newIntel = {}

      symbols.forEach((sym, idx) => {
        if (quoteResponses[idx]?.data) {
          newQuotes[sym] = quoteResponses[idx].data
        }
        if (intelResponses[idx]?.data) {
          newIntel[sym] = intelResponses[idx].data
        }
      })

      setQuotesMap((prev) => ({ ...prev, ...newQuotes }))
      setIntelligenceMap((prev) => ({ ...prev, ...newIntel }))
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
    }
  }, [activeWatchlist])

  useEffect(() => {
    let isCancelled = false
    const init = async () => {
      try {
        await loadWatchlistData()
      } catch (err) {
        if (!isCancelled) setError(err)
      }
    }
    init()
    return () => {
      isCancelled = true
    }
  }, [loadWatchlistData])

  const handleCreateWatchlist = (e) => {
    e.preventDefault()
    if (!newWlName.trim()) return

    const parsedSymbols = newWlSymbols
      .split(/[\s,]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)

    const newWl = {
      id: `wl-custom-${Date.now()}`,
      name: newWlName.trim(),
      description: newWlDesc.trim() || 'Custom curated watchlist',
      symbols: parsedSymbols.length > 0 ? parsedSymbols : ['SPY'],
      category: 'custom',
    }

    setWatchlists((prev) => [...prev, newWl])
    setActiveWatchlistId(newWl.id)
    setIsNewWlOpen(false)
    setNewWlName('')
    setNewWlDesc('')
    setNewWlSymbols('')
  }

  // Calculate watchlist metrics
  const activeSymbols = activeWatchlist?.symbols || []
  let bullishCount = 0
  let totalScore = 0
  let scoredCount = 0
  let totalChangePct = 0

  activeSymbols.forEach((sym) => {
    const q = quotesMap[sym]
    if (q?.change_percent !== undefined) {
      totalChangePct += Number(q.change_percent)
    }
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

  const avgChange = activeSymbols.length
    ? (totalChangePct / activeSymbols.length).toFixed(2)
    : '0.00'
  const avgScore = scoredCount ? Math.round(totalScore / scoredCount) : 60
  const bullPct = activeSymbols.length
    ? Math.round((bullishCount / activeSymbols.length) * 100)
    : 50

  const activeInstrumentForModal = selectedSymbol
    ? {
        symbol: selectedSymbol,
        name: SYMBOL_NAMES[selectedSymbol] || selectedSymbol,
        assetType: selectedSymbol.includes('-')
          ? 'crypto'
          : selectedSymbol === 'SPY' || selectedSymbol === 'QQQ'
          ? 'etf'
          : 'equity',
        price: quotesMap[selectedSymbol]?.price ?? 0,
        change: `${Number(quotesMap[selectedSymbol]?.change_percent ?? 0) >= 0 ? '+' : ''}${Number(quotesMap[selectedSymbol]?.change_percent ?? 0).toFixed(2)}%`,
        isUp: Number(quotesMap[selectedSymbol]?.change_percent ?? 0) >= 0,
      }
    : null

  return (
    <div id="cf-watchlists-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Optional Error Alert */}
      {error && (
        <ErrorBanner
          error={error}
          onRetry={loadWatchlistData}
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
          onClick={() => setIsNewWlOpen(true)}
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
        }}
      >
        {watchlists.map((wl) => {
          const isActive = wl.id === activeWatchlistId
          return (
            <button
              key={wl.id}
              id={`cf-wl-tab-${wl.id}`}
              onClick={() => setActiveWatchlistId(wl.id)}
              style={{
                background: isActive ? 'var(--cf-bg-surface-elevated)' : 'transparent',
                border: `1px solid ${isActive ? 'var(--cf-border-focus)' : 'var(--cf-border)'}`,
                color: isActive ? 'var(--cf-text-primary)' : 'var(--cf-text-secondary)',
                borderRadius: 'var(--cf-radius-md)',
                padding: '10px 16px',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
                minWidth: '200px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '13px' }}>{wl.name}</span>
                <Badge variant={isActive ? 'brand' : 'neutral'} size="sm">
                  {wl.symbols.length}
                </Badge>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>
                {wl.description}
              </span>
            </button>
          )
        })}
      </div>

      {/* Loading Spinner */}
      {isLoading && (
        <LoadingSpinner message={`Syncing quotes and technical postures for ${activeWatchlist?.name}...`} id="cf-wl-spinner" />
      )}

      {/* Watchlist Aggregate Performance & Posture Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--cf-space-4)' }}>
        <StatWidget
          id="stat-wl-drift"
          title="Average Daily Drift"
          value={`${Number(avgChange) >= 0 ? '+' : ''}${avgChange}%`}
          changePercent={Number(avgChange)}
          subtitle={`${activeSymbols.length} instruments observed`}
        />
        <StatWidget
          id="stat-wl-posture"
          title="Technical Consensus"
          value={`${bullPct}% Bullish`}
          changePercent={bullPct >= 50 ? 1.0 : -1.0}
          subtitle={`${bullishCount} of ${activeSymbols.length} in constructive trend`}
        />
        <StatWidget
          id="stat-wl-score"
          title="Consensus Factor Score"
          value={`${avgScore} / 100`}
          changePercent={0.0}
          subtitle={avgScore >= 60 ? 'Strong Quantitative Support' : 'Balanced Stance'}
        />
        <StatWidget
          id="stat-wl-count"
          title="Active Watchlist"
          value={activeWatchlist?.name || 'Default'}
          changePercent={0.0}
          subtitle={`${activeSymbols.join(', ')}`}
        />
      </div>

      {/* Watchlist Table with Technical Posture Pills */}
      <Card
        id="cf-watchlist-table-card"
        title={`${activeWatchlist?.name} (${activeSymbols.length} Assets)`}
        subtitle={activeWatchlist?.description}
        action={
          <button
            id="cf-btn-refresh-wl"
            onClick={loadWatchlistData}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--cf-brand-cyan)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ↻ Refresh Postures & Quotes
          </button>
        }
      >
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>INSTRUMENT</th>
                <th style={{ padding: '12px 16px', fontWeight: 600 }}>ASSET CLASS</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>PRICE (USD)</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>24H CHANGE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>TECHNICAL POSTURE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>MOMENTUM STATE</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>VOLATILITY</th>
                <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {activeSymbols.map((sym) => {
                const quote = quotesMap[sym]
                const intel = intelligenceMap[sym]
                const price = quote?.price ? Number(quote.price) : 0
                const changePct = quote?.change_percent !== undefined ? Number(quote.change_percent) : 0
                const isUp = changePct >= 0
                const isCrypto = sym.includes('-')
                const isEtf = sym === 'SPY' || sym === 'QQQ'
                const assetType = isCrypto ? 'crypto' : isEtf ? 'etf' : 'equity'

                return (
                  <tr
                    key={sym}
                    id={`wl-row-${sym}`}
                    onClick={() => setSelectedSymbol(sym)}
                    style={{
                      borderBottom: '1px solid var(--cf-border)',
                      cursor: 'pointer',
                      transition: 'background var(--cf-transition-fast)',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                    onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                  >
                    <td style={{ padding: '14px 16px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--cf-brand-cyan)' }}>{sym}</div>
                      <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)' }}>
                        {SYMBOL_NAMES[sym] || sym}
                      </div>
                    </td>
                    <td style={{ padding: '14px 16px' }}>
                      <Badge variant={isCrypto ? 'brand' : isEtf ? 'warning' : 'neutral'} size="sm">
                        {assetType}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                      ${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                      <span style={{ color: isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 700 }}>
                        {isUp ? '+' : ''}{changePct.toFixed(2)}%
                      </span>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <TechnicalPostureBadge
                        posture={intel}
                        showScore
                        size="sm"
                        id={`wl-posture-${sym}`}
                      />
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'center', fontSize: '12px', color: 'var(--cf-text-secondary)' }}>
                      {intel?.momentum_state?.replace(/_/g, ' ') || 'Neutral'}
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <Badge variant="neutral" size="sm">
                        {intel?.volatility_regime || 'Normal'}
                      </Badge>
                    </td>
                    <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                      <button
                        id={`btn-inspect-wl-${sym}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedSymbol(sym)
                        }}
                        style={{
                          background: 'rgba(59, 130, 246, 0.12)',
                          color: 'var(--cf-brand-primary)',
                          border: '1px solid rgba(59, 130, 246, 0.25)',
                          borderRadius: 'var(--cf-radius-sm)',
                          padding: '4px 10px',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Inspect & Chart
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Modal: New Watchlist */}
      {isNewWlOpen && (
        <div
          id="cf-new-wl-modal-backdrop"
          onClick={() => setIsNewWlOpen(false)}
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
            id="cf-new-wl-modal-content"
            onClick={(e) => e.stopPropagation()}
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
              <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--cf-text-primary)' }}>
                Create Custom Watchlist
              </h3>
              <button
                onClick={() => setIsNewWlOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--cf-text-secondary)',
                  fontSize: '18px',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateWatchlist} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-4)' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '4px' }}>
                  Watchlist Name *
                </label>
                <input
                  id="input-new-wl-name"
                  type="text"
                  placeholder="e.g. Clean Energy Leaders"
                  value={newWlName}
                  onChange={(e) => setNewWlName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '4px' }}>
                  Description
                </label>
                <input
                  id="input-new-wl-desc"
                  type="text"
                  placeholder="e.g. Focus basket on solar and grid storage"
                  value={newWlDesc}
                  onChange={(e) => setNewWlDesc(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '4px' }}>
                  Symbols (comma or space separated)
                </label>
                <input
                  id="input-new-wl-symbols"
                  type="text"
                  placeholder="e.g. NVDA, MSFT, AAPL"
                  value={newWlSymbols}
                  onChange={(e) => setNewWlSymbols(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--cf-space-2)' }}>
                <button
                  type="button"
                  onClick={() => setIsNewWlOpen(false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--cf-border)',
                    color: 'var(--cf-text-secondary)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 14px',
                    fontSize: '13px',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  id="btn-submit-new-wl"
                  type="submit"
                  style={{
                    background: 'var(--cf-brand-gradient)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 16px',
                    fontSize: '13px',
                    fontWeight: 600,
                    boxShadow: 'var(--cf-brand-glow)',
                    cursor: 'pointer',
                  }}
                >
                  Create Watchlist
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Asset Detail Experience Modal Integration */}
      {selectedSymbol && activeInstrumentForModal && (
        <AssetDetailModal
          instrument={activeInstrumentForModal}
          quote={quotesMap[selectedSymbol]}
          intelligence={intelligenceMap[selectedSymbol]}
          onClose={() => setSelectedSymbol(null)}
        />
      )}
    </div>
  )
}
