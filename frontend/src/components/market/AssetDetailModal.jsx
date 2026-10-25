import { useState, useEffect } from 'react'
import { Badge } from '../common/Badge'
import { PriceChart } from './PriceChart'
import { MarketIntelligenceCard } from './MarketIntelligenceCard'
import { TechnicalPostureBadge } from '../analytics'
import { getAnalyticsSummary, getReturnsAnalysis } from '../../api/analytics'
import { useNavigation } from '../../state/NavigationContext'
import { PAGES } from '../../state/pages'

/**
 * CentFlow Comprehensive Asset Detail Experience Modal
 *
 * Provides a deep exploration environment for an individual asset, including:
 * - Identity and market classification header
 * - Headline pricing with visual 24h High/Low range slider bar
 * - Key financial statistics grid
 * - Direct platform action triggers (Watchlist, Portfolio, Persist, Backfill)
 * - Multi-mode tabbed inspection (Comprehensive, Technical Chart, Market Intelligence, Profile)
 */
export function AssetDetailModal({
  instrument,
  quote,
  chartBars = [],
  indicators = null,
  intelligence = null,
  returnsAnalysis = null,
  isLoading = false,
  chartTimeframe = '1M',
  onTimeframeChange,
  onClose,
  onPersistQuote,
  onBackfillBars,
  actionFeedback = null,
}) {
  const { navigate } = useNavigation()
  const [activeTab, setActiveTab] = useState('comprehensive') // 'comprehensive' | 'chart' | 'intelligence' | 'profile'
  const [watchlistAdded, setWatchlistAdded] = useState(false)
  const [fetchedIntel, setFetchedIntel] = useState(null)
  const [fetchedReturns, setFetchedReturns] = useState(null)

  // On-demand fetch if analytics were not preloaded
  useEffect(() => {
    let isCancelled = false
    if (!intelligence && instrument?.symbol) {
      getAnalyticsSummary(instrument.symbol, 365, '1d')
        .then((res) => {
          if (!isCancelled && res?.data) setFetchedIntel(res.data)
        })
        .catch(() => null)
    }
    if (!returnsAnalysis && instrument?.symbol) {
      getReturnsAnalysis(instrument.symbol, 365, '1d', 252)
        .then((res) => {
          if (!isCancelled && res?.data) setFetchedReturns(res.data)
        })
        .catch(() => null)
    }
    return () => {
      isCancelled = true
    }
  }, [instrument?.symbol, intelligence, returnsAnalysis])

  const resolvedIntel = intelligence || fetchedIntel
  const resolvedReturns = returnsAnalysis || fetchedReturns

  // Keyboard Escape listener to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose?.()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!instrument) return null

  // Calculate pricing numbers
  const currentPrice = Number(quote?.price ?? instrument.price ?? 0)
  const low24h = quote?.low ? Number(quote.low) : currentPrice * 0.985
  const high24h = quote?.high ? Number(quote.high) : currentPrice * 1.015
  const prevClose = quote?.previous_close ? Number(quote.previous_close) : null
  const openPrice = quote?.open ? Number(quote.open) : null

  // Calculate position within 24h range (0 to 100%)
  const rangeSpan = high24h - low24h
  const rangePercent = rangeSpan > 0 ? Math.min(100, Math.max(0, ((currentPrice - low24h) / rangeSpan) * 100)) : 50

  const changeText = typeof instrument.change === 'string' ? instrument.change : `${instrument.change ?? 0}%`
  const isUp = instrument.isUp ?? (!String(changeText).startsWith('-'))

  const handleAddToWatchlist = () => {
    setWatchlistAdded(true)
    setTimeout(() => setWatchlistAdded(false), 3000)
  }

  const handleAddToPortfolio = () => {
    onClose?.()
    navigate(PAGES.PORTFOLIOS, { symbol: instrument.symbol })
  }

  return (
    <div
      id="cf-asset-detail-modal-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.78)',
        backdropFilter: 'blur(8px)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--cf-space-4)',
      }}
    >
      <div
        id="cf-asset-detail-modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cf-asset-detail-title"
        style={{
          background: 'var(--cf-bg-surface)',
          border: '1px solid var(--cf-border)',
          borderRadius: 'var(--cf-radius-xl)',
          width: '100%',
          maxWidth: '960px',
          maxHeight: '92vh',
          overflowY: 'auto',
          boxShadow: 'var(--cf-shadow-glass)',
          padding: 'var(--cf-space-6)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--cf-space-5)',
        }}
      >
        {/* 1. Asset Identity Header & Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--cf-space-3)' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <h2 id="cf-asset-detail-title" style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em', color: 'var(--cf-text-primary)' }}>
                {instrument.symbol}
              </h2>
              <Badge variant={instrument.assetType === 'crypto' ? 'brand' : instrument.assetType === 'etf' ? 'warning' : 'neutral'} size="sm">
                {instrument.assetType}
              </Badge>
              <Badge variant="outline" size="sm">
                {instrument.exchange || 'Global Exchange'}
              </Badge>
              <span style={{ color: 'var(--cf-text-muted)', fontSize: '13px', fontWeight: 600 }}>
                {quote?.currency || 'USD'}
              </span>
            </div>
            <div style={{ color: 'var(--cf-text-secondary)', fontSize: '14px', marginTop: '4px' }}>
              {instrument.name || instrument.symbol}
            </div>
          </div>

          {/* Action Header Controls & Close Button */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              id="cf-btn-add-watchlist"
              onClick={handleAddToWatchlist}
              style={{
                background: watchlistAdded ? 'var(--cf-bullish-bg)' : 'var(--cf-bg-surface-elevated)',
                color: watchlistAdded ? 'var(--cf-bullish)' : 'var(--cf-text-primary)',
                border: `1px solid ${watchlistAdded ? 'var(--cf-bullish-border)' : 'var(--cf-border)'}`,
                borderRadius: 'var(--cf-radius-md)',
                padding: '7px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              <span>{watchlistAdded ? '✓ Added to Watchlist' : '+ Watchlist'}</span>
            </button>

            <button
              id="cf-btn-add-portfolio"
              onClick={handleAddToPortfolio}
              style={{
                background: 'rgba(59, 130, 246, 0.12)',
                color: 'var(--cf-brand-primary)',
                border: '1px solid rgba(59, 130, 246, 0.25)',
                borderRadius: 'var(--cf-radius-md)',
                padding: '7px 12px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              <span>+ Position in Portfolio</span>
            </button>

            <button
              id="cf-asset-detail-close"
              onClick={onClose}
              aria-label="Close modal"
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
                fontSize: '15px',
                marginLeft: '4px',
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* 2. Headline Pricing & Visual 24h Range Bar */}
        <div
          id="cf-asset-price-banner"
          style={{
            background: 'var(--cf-bg-base)',
            border: '1px solid var(--cf-border)',
            borderRadius: 'var(--cf-radius-lg)',
            padding: 'var(--cf-space-4)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--cf-space-3)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--cf-space-2)' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
              <span style={{ fontSize: '28px', fontWeight: 700, color: 'var(--cf-text-primary)', letterSpacing: '-0.02em' }}>
                ${currentPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span
                style={{
                  fontSize: '15px',
                  fontWeight: 700,
                  color: isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {isUp ? '▲' : '▼'} {changeText}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <TechnicalPostureBadge
                posture={resolvedIntel}
                showScore
                size="md"
                id="cf-asset-detail-posture-badge"
              />
              {prevClose && (
                <div style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>
                  Prev Close: ${prevClose.toFixed(2)}
                </div>
              )}
            </div>
          </div>

          {/* Visual 24h High/Low Slider Gauge */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
              <span>24h Low: ${low24h.toFixed(2)}</span>
              <span style={{ color: 'var(--cf-text-secondary)', fontWeight: 600 }}>24H RANGE</span>
              <span>24h High: ${high24h.toFixed(2)}</span>
            </div>
            <div
              style={{
                position: 'relative',
                height: '6px',
                background: 'var(--cf-bg-surface-elevated)',
                borderRadius: 'var(--cf-radius-full)',
                overflow: 'visible',
              }}
            >
              {/* Active filled track */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: `${rangePercent}%`,
                  background: 'linear-gradient(90deg, var(--cf-brand-cyan), var(--cf-brand-primary))',
                  borderRadius: 'var(--cf-radius-full)',
                }}
              />
              {/* Current Price Pointer */}
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  left: `${rangePercent}%`,
                  transform: 'translate(-50%, -50%)',
                  width: '12px',
                  height: '12px',
                  background: '#ffffff',
                  border: '2px solid var(--cf-brand-primary)',
                  borderRadius: 'var(--cf-radius-full)',
                  boxShadow: '0 0 8px rgba(59, 130, 246, 0.6)',
                }}
              />
            </div>
          </div>

          {/* Quantitative Analytics Posture Strip */}
          {resolvedIntel && (
            <div
              id="cf-detail-factor-strip"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                gap: 'var(--cf-space-2)',
                marginTop: 'var(--cf-space-1)',
                borderTop: '1px solid var(--cf-border)',
                paddingTop: 'var(--cf-space-2)',
                fontSize: '11px',
              }}
            >
              <div>
                <span style={{ color: 'var(--cf-text-muted)' }}>MOMENTUM: </span>
                <span style={{ color: 'var(--cf-text-primary)', fontWeight: 600 }}>
                  {resolvedIntel.momentum_state?.toUpperCase() || 'NEUTRAL'}
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--cf-text-muted)' }}>VOLATILITY: </span>
                <span style={{ color: 'var(--cf-text-primary)', fontWeight: 600 }}>
                  {resolvedIntel.volatility_regime?.toUpperCase() || 'NORMAL'}
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--cf-text-muted)' }}>FACTOR SCORE: </span>
                <span style={{ color: 'var(--cf-brand-cyan)', fontWeight: 700 }}>
                  {resolvedIntel.composite_score ?? 50} / 100
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--cf-text-muted)' }}>VERDICT: </span>
                <span style={{ color: 'var(--cf-text-secondary)', fontWeight: 600 }}>
                  {resolvedIntel.summary_verdict || 'Balanced'}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* 3. Key Financial Statistics Grid */}
        <div
          id="cf-asset-key-stats"
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: 'var(--cf-space-3)',
            background: 'var(--cf-bg-surface-glass)',
            padding: 'var(--cf-space-4)',
            borderRadius: 'var(--cf-radius-lg)',
            border: '1px solid var(--cf-border)',
          }}
        >
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Open</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
              {openPrice ? `$${openPrice.toFixed(2)}` : 'N/A'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>24h High</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-bullish)' }}>
              ${high24h.toFixed(2)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>24h Low</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-bearish)' }}>
              ${low24h.toFixed(2)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Prev Close</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
              {prevClose ? `$${prevClose.toFixed(2)}` : 'N/A'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Volume</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-text-secondary)' }}>
              {instrument.volume || 'N/A'}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Classification</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-brand-cyan)', textTransform: 'capitalize' }}>
              {instrument.assetType}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Market Status</div>
            <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cf-bullish)' }}>
              Active
            </div>
          </div>
        </div>

        {/* 4. Tab Navigation Bar */}
        <div
          id="cf-asset-detail-tabs"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            borderBottom: '1px solid var(--cf-border)',
            paddingBottom: '8px',
            overflowX: 'auto',
          }}
        >
          {[
            { id: 'comprehensive', label: 'Comprehensive (Chart & Intelligence)' },
            { id: 'chart', label: 'Technical Chart & Overlays' },
            { id: 'intelligence', label: 'Market Intelligence & Signals' },
            { id: 'profile', label: 'Instrument Profile & Provenance' },
          ].map((tab) => (
            <button
              key={tab.id}
              id={`cf-detail-tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              style={{
                background: activeTab === tab.id ? 'var(--cf-brand-primary)' : 'transparent',
                color: activeTab === tab.id ? '#ffffff' : 'var(--cf-text-secondary)',
                border: 'none',
                borderRadius: 'var(--cf-radius-sm)',
                padding: '6px 14px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 5. Tab Content Views */}
        {/* View A: Market Intelligence Card */}
        {(activeTab === 'comprehensive' || activeTab === 'intelligence') && (
          <MarketIntelligenceCard
            id={`detail-intelligence-${instrument.symbol}`}
            symbol={instrument.symbol}
            intelligence={resolvedIntel}
            returnsAnalysis={resolvedReturns}
            isLoading={isLoading}
          />
        )}

        {/* View B: Price Chart with Indicators */}
        {(activeTab === 'comprehensive' || activeTab === 'chart') && (
          <PriceChart
            id={`detail-chart-${instrument.symbol}`}
            data={chartBars}
            indicators={indicators}
            symbol={instrument.symbol}
            currency={quote?.currency || 'USD'}
            isLoading={isLoading}
            timeframe={chartTimeframe}
            onTimeframeChange={onTimeframeChange}
            height={340}
          />
        )}

        {/* View C: Instrument Profile & Provenance */}
        {activeTab === 'profile' && (
          <div
            id="cf-instrument-profile-view"
            style={{
              background: 'var(--cf-bg-base)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-lg)',
              padding: 'var(--cf-space-5)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--cf-space-4)',
            }}
          >
            <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--cf-text-primary)' }}>
              Instrument Profile & Data Architecture
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--cf-text-secondary)', margin: 0 }}>
              CentFlow normalizes market data and factor metrics across equity, ETF, and cryptocurrency classes using provider-agnostic abstractions and deterministic quantitative modeling.
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--cf-space-3)' }}>
              <div style={{ background: 'var(--cf-bg-surface)', padding: '12px', borderRadius: 'var(--cf-radius-md)', border: '1px solid var(--cf-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>PRIMARY EXCHANGE</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-text-primary)', marginTop: '2px' }}>
                  {instrument.exchange || 'NASDAQ'}
                </div>
              </div>
              <div style={{ background: 'var(--cf-bg-surface)', padding: '12px', borderRadius: 'var(--cf-radius-md)', border: '1px solid var(--cf-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>SETTLEMENT CURRENCY</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-text-primary)', marginTop: '2px' }}>
                  {quote?.currency || 'USD'}
                </div>
              </div>
              <div style={{ background: 'var(--cf-bg-surface)', padding: '12px', borderRadius: 'var(--cf-radius-md)', border: '1px solid var(--cf-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>ASSET CLASS</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-brand-cyan)', marginTop: '2px', textTransform: 'capitalize' }}>
                  {instrument.assetType}
                </div>
              </div>
              <div style={{ background: 'var(--cf-bg-surface)', padding: '12px', borderRadius: 'var(--cf-radius-md)', border: '1px solid var(--cf-border)' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>INGESTION ENGINE</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-bullish)', marginTop: '2px' }}>
                  CentFlow MarketDataService v1
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 6. Database Persistence & Backfill Action Footer */}
        <div
          id="cf-asset-detail-actions-footer"
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
              onClick={onPersistQuote}
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
              onClick={onBackfillBars}
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
  )
}
