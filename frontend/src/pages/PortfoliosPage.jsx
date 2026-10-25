import { useState, useEffect, useCallback } from 'react'
import { Card } from '../components/common/Card'
import { StatWidget } from '../components/market/StatWidget'
import { Badge } from '../components/common/Badge'
import { LoadingSpinner } from '../components/common/LoadingSpinner'
import { ErrorBanner } from '../components/common/ErrorBanner'
import { useNavigation } from '../state/NavigationContext'
import { TechnicalPostureBadge } from '../components/analytics'
import { AssetDetailModal } from '../components/market/AssetDetailModal'
import { getAnalyticsSummary } from '../api/analytics'
import {
  listPortfolios,
  createPortfolio,
  addPosition,
  removePosition,
} from '../api/portfolios'

export function PortfoliosPage() {
  const { pageParams } = useNavigation()
  const [portfolios, setPortfolios] = useState([])
  const [activePortfolioId, setActivePortfolioId] = useState(null)
  const [portfolioIntelMap, setPortfolioIntelMap] = useState({})
  const [inspectInstrument, setInspectInstrument] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [actionFeedback, setActionFeedback] = useState(null)

  // Position Modal State (auto-opened if navigated with symbol param)
  const [isAddPosOpen, setIsAddPosOpen] = useState(() => Boolean(pageParams?.symbol))
  const [posSymbol, setPosSymbol] = useState(() => (pageParams?.symbol ? pageParams.symbol.toUpperCase() : ''))
  const [posQuantity, setPosQuantity] = useState('')
  const [posPrice, setPosPrice] = useState('')
  const [isSubmittingPos, setIsSubmittingPos] = useState(false)

  // Portfolio Creation Modal State
  const [isNewPfOpen, setIsNewPfOpen] = useState(false)
  const [newPfName, setNewPfName] = useState('')
  const [newPfDesc, setNewPfDesc] = useState('')
  const [isSubmittingPf, setIsSubmittingPf] = useState(false)

  // Load portfolios from backend
  const loadPortfolios = useCallback(async () => {
    setError(null)
    setIsLoading(true)
    try {
      const res = await listPortfolios()
      if (res?.data && res.data.length > 0) {
        setPortfolios(res.data)
        setActivePortfolioId((prev) => (prev ? prev : res.data[0].id))
      }
    } catch (err) {
      setError(err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    let isCancelled = false
    const init = async () => {
      try {
        const res = await listPortfolios()
        if (!isCancelled && res?.data && res.data.length > 0) {
          setPortfolios(res.data)
          setActivePortfolioId((prev) => (prev ? prev : res.data[0].id))
        }
      } catch (err) {
        if (!isCancelled) setError(err)
      }
    }
    init()
    return () => {
      isCancelled = true
    }
  }, [])

  const activePortfolio =
    portfolios.find((p) => p.id === activePortfolioId) || portfolios[0] || null

  // On-demand fetch of analytics intelligence for active holdings
  useEffect(() => {
    let isCancelled = false
    const posList = activePortfolio?.positions || []
    if (!posList.length) return

    const distinctSymbols = [...new Set(posList.map((p) => p.symbol))]
    Promise.all(
      distinctSymbols.map((sym) =>
        getAnalyticsSummary(sym, 365, '1d').catch(() => null)
      )
    ).then((results) => {
      if (isCancelled) return
      const intelMap = {}
      distinctSymbols.forEach((sym, idx) => {
        if (results[idx]?.data) {
          intelMap[sym] = results[idx].data
        }
      })
      setPortfolioIntelMap((prev) => ({ ...prev, ...intelMap }))
    })

    return () => {
      isCancelled = true
    }
  }, [activePortfolio?.positions])

  const handleCreatePortfolio = async (e) => {
    e.preventDefault()
    if (!newPfName.trim()) return
    setIsSubmittingPf(true)
    try {
      const res = await createPortfolio({
        name: newPfName.trim(),
        description: newPfDesc.trim(),
        baseCurrency: 'USD',
      })
      if (res?.data) {
        setPortfolios((prev) => [res.data, ...prev])
        setActivePortfolioId(res.data.id)
        setIsNewPfOpen(false)
        setNewPfName('')
        setNewPfDesc('')
        setActionFeedback({ type: 'success', message: `Portfolio "${res.data.name}" created.` })
      }
    } catch (err) {
      setActionFeedback({ type: 'error', message: err.message || 'Failed to create portfolio.' })
    } finally {
      setIsSubmittingPf(false)
    }
  }

  const handleAddPositionSubmit = async (e) => {
    e.preventDefault()
    if (!activePortfolio || !posSymbol.trim() || !posQuantity || !posPrice) return
    setIsSubmittingPos(true)
    try {
      const res = await addPosition(activePortfolio.id, {
        symbol: posSymbol.trim().toUpperCase(),
        quantity: posQuantity,
        averagePrice: posPrice,
        currency: 'USD',
      })
      if (res?.data) {
        setPortfolios((prev) =>
          prev.map((p) => (p.id === res.data.id ? res.data : p))
        )
        setIsAddPosOpen(false)
        setPosSymbol('')
        setPosQuantity('')
        setPosPrice('')
        setActionFeedback({
          type: 'success',
          message: `Position in ${posSymbol.toUpperCase()} added to ${activePortfolio.name}.`,
        })
      }
    } catch (err) {
      setActionFeedback({ type: 'error', message: err.message || 'Failed to add position.' })
    } finally {
      setIsSubmittingPos(false)
    }
  }

  const handleRemovePosition = async (posId, symbol) => {
    if (!activePortfolio) return
    try {
      const res = await removePosition(activePortfolio.id, posId)
      if (res?.data) {
        setPortfolios((prev) =>
          prev.map((p) => (p.id === res.data.id ? res.data : p))
        )
        setActionFeedback({
          type: 'info',
          message: `Closed position in ${symbol}.`,
        })
      }
    } catch (err) {
      setActionFeedback({ type: 'error', message: err.message || 'Failed to remove position.' })
    }
  }

  const totalValuation = activePortfolio ? Number(activePortfolio.total_valuation) : 0
  const totalCost = activePortfolio ? Number(activePortfolio.total_cost_basis) : 0
  const totalPnl = activePortfolio ? Number(activePortfolio.total_unrealized_pnl) : 0
  const totalPnlPct = activePortfolio ? Number(activePortfolio.total_unrealized_pnl_percent) : 0
  const positions = activePortfolio?.positions || []

  // Aggregate Risk and Volatility exposure calculations
  let weightedFactorScoreSum = 0
  let bullValue = 0
  let bearValue = 0
  let neutValue = 0
  let equityValue = 0
  let cryptoValue = 0
  let etfValue = 0
  const portfolioVolCounts = { low: 0, normal: 0, high: 0, extreme: 0 }

  positions.forEach((pos) => {
    const mv = Number(pos.market_value || 0)
    const intel = portfolioIntelMap[pos.symbol]
    const score = intel?.composite_score !== undefined ? Number(intel.composite_score) : 50
    weightedFactorScoreSum += mv * score

    const posture = String(intel?.trend_posture || '').toLowerCase()
    if (posture.includes('bull') || posture.includes('golden')) {
      bullValue += mv
    } else if (posture.includes('bear') || posture.includes('death')) {
      bearValue += mv
    } else {
      neutValue += mv
    }

    const assetClass = String(pos.asset_type || '').toLowerCase()
    if (assetClass === 'crypto') {
      cryptoValue += mv
    } else if (assetClass === 'etf') {
      etfValue += mv
    } else {
      equityValue += mv
    }

    const vol = String(intel?.volatility_regime || 'normal').toLowerCase()
    if (portfolioVolCounts[vol] !== undefined) {
      portfolioVolCounts[vol] += 1
    } else {
      portfolioVolCounts.normal += 1
    }
  })

  const portfolioWeightedScore = totalValuation > 0
    ? Math.round(weightedFactorScoreSum / totalValuation)
    : 55
  const portfolioBullPct = totalValuation > 0
    ? Math.round((bullValue / totalValuation) * 100)
    : 0
  const portfolioBearPct = totalValuation > 0
    ? Math.round((bearValue / totalValuation) * 100)
    : 0
  const portfolioNeutPct = Math.max(0, 100 - portfolioBullPct - portfolioBearPct)
  const equityPct = totalValuation > 0 ? Math.round((equityValue / totalValuation) * 100) : 0
  const cryptoPct = totalValuation > 0 ? Math.round((cryptoValue / totalValuation) * 100) : 0
  const etfPct = totalValuation > 0 ? Math.round((etfValue / totalValuation) * 100) : 0

  return (
    <div id="cf-portfolios-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Optional Error Alert */}
      {error && (
        <ErrorBanner
          error={error}
          onRetry={loadPortfolios}
          id="cf-portfolios-error-banner"
        />
      )}

      {/* Action Notification */}
      {actionFeedback && (
        <div
          id="cf-portfolio-feedback-banner"
          style={{
            background:
              actionFeedback.type === 'success'
                ? 'var(--cf-bullish-bg)'
                : actionFeedback.type === 'error'
                ? 'var(--cf-bearish-bg)'
                : 'rgba(59, 130, 246, 0.12)',
            border: `1px solid ${
              actionFeedback.type === 'success'
                ? 'var(--cf-bullish-border)'
                : actionFeedback.type === 'error'
                ? 'var(--cf-bearish-border)'
                : 'rgba(59, 130, 246, 0.25)'
            }`,
            borderRadius: 'var(--cf-radius-md)',
            padding: '10px 16px',
            fontSize: '13px',
            fontWeight: 600,
            color:
              actionFeedback.type === 'success'
                ? 'var(--cf-bullish)'
                : actionFeedback.type === 'error'
                ? 'var(--cf-bearish)'
                : 'var(--cf-brand-cyan)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>{actionFeedback.message}</span>
          <button
            onClick={() => setActionFeedback(null)}
            style={{ background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Header and Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Portfolios & Holdings</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Multi-asset position tracking, real-time marked-to-market valuation, and unrealized return metrics.
          </p>
        </div>

        {/* Portfolio Selection & Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {portfolios.length > 1 && (
            <select
              id="cf-portfolio-selector"
              value={activePortfolioId || ''}
              onChange={(e) => setActivePortfolioId(e.target.value)}
              style={{
                background: 'var(--cf-bg-surface-elevated)',
                border: '1px solid var(--cf-border)',
                borderRadius: 'var(--cf-radius-md)',
                color: 'var(--cf-text-primary)',
                padding: '9px 12px',
                fontSize: '13px',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {portfolios.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.positions_count} assets)
                </option>
              ))}
            </select>
          )}

          <button
            id="cf-btn-open-add-pos"
            onClick={() => setIsAddPosOpen(true)}
            style={{
              background: 'var(--cf-brand-gradient)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 'var(--cf-radius-md)',
              padding: '9px 16px',
              fontSize: '13px',
              fontWeight: 600,
              boxShadow: 'var(--cf-brand-glow)',
              cursor: 'pointer',
            }}
          >
            + Add Holding
          </button>

          <button
            id="cf-btn-open-new-pf"
            onClick={() => setIsNewPfOpen(true)}
            style={{
              background: 'var(--cf-bg-surface-elevated)',
              color: 'var(--cf-text-primary)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '9px 14px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            + New Portfolio
          </button>
        </div>
      </div>

      {/* Loading Indicator */}
      {isLoading && (
        <LoadingSpinner message="Calculating real-time marked-to-market valuations..." id="cf-portfolio-spinner" />
      )}

      {/* Portfolio Performance KPIs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--cf-space-4)' }}>
        <StatWidget
          id="stat-portfolio-val"
          title="Total Valuation"
          value={`$${totalValuation.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          changePercent={totalPnlPct}
          subtitle={`Active Portfolio: ${activePortfolio?.name || 'Default'}`}
        />
        <StatWidget
          id="stat-portfolio-pnl"
          title="Unrealized P&L"
          value={`${totalPnl >= 0 ? '+' : ''}$${totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          changePercent={totalPnlPct}
          subtitle={`Return on invested cost: ${totalPnlPct >= 0 ? '+' : ''}${totalPnlPct.toFixed(2)}%`}
        />
        <StatWidget
          id="stat-portfolio-cost"
          title="Invested Cost Basis"
          value={`$${totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          changePercent={0.0}
          subtitle="Cumulative acquisition cost"
        />
        <StatWidget
          id="stat-portfolio-holdings"
          title="Active Holdings"
          value={`${positions.length} Positions`}
          changePercent={positions.length > 0 ? 1.0 : 0.0}
          subtitle={`Base Currency: ${activePortfolio?.base_currency || 'USD'}`}
        />
      </div>

      {/* Aggregate Risk & Volatility Exposure Card */}
      {positions.length > 0 && (
        <Card
          id="cf-portfolio-risk-card"
          title="Aggregate Risk & Volatility Exposure"
          subtitle="Capital concentration, trend alignment, and quantitative factor health"
          action={
            <Badge variant={portfolioWeightedScore >= 60 ? 'bullish' : portfolioWeightedScore <= 40 ? 'bearish' : 'neutral'} size="sm">
              {portfolioWeightedScore >= 60 ? 'Favorable Risk Stance' : portfolioWeightedScore <= 40 ? 'Defensive Stance' : 'Balanced Exposure'}
            </Badge>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-4)' }}>
            {/* Trend Posture Distribution Track */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                <span style={{ color: 'var(--cf-text-secondary)', fontWeight: 600 }}>Trend Posture Exposure (by Market Value)</span>
                <div style={{ display: 'flex', gap: '12px', fontSize: '11px', fontWeight: 600 }}>
                  <span style={{ color: 'var(--cf-bullish)' }}>▲ {portfolioBullPct}% Bullish (${bullValue.toLocaleString(undefined, { maximumFractionDigits: 0 })})</span>
                  <span style={{ color: 'var(--cf-text-muted)' }}>■ {portfolioNeutPct}% Neutral (${neutValue.toLocaleString(undefined, { maximumFractionDigits: 0 })})</span>
                  <span style={{ color: 'var(--cf-bearish)' }}>▼ {portfolioBearPct}% Bearish (${bearValue.toLocaleString(undefined, { maximumFractionDigits: 0 })})</span>
                </div>
              </div>
              <div
                style={{
                  display: 'flex',
                  height: '8px',
                  borderRadius: 'var(--cf-radius-full)',
                  overflow: 'hidden',
                  background: 'var(--cf-bg-surface-elevated)',
                }}
              >
                <div style={{ width: `${portfolioBullPct}%`, background: 'var(--cf-bullish)' }} />
                <div style={{ width: `${portfolioNeutPct}%`, background: 'var(--cf-border-strong)' }} />
                <div style={{ width: `${portfolioBearPct}%`, background: 'var(--cf-bearish)' }} />
              </div>
            </div>

            {/* Metrics 3-Col Grid: Weighted Factor Health, Asset Class Allocation, Volatility Regimes */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--cf-space-3)' }}>
              <div style={{ background: 'var(--cf-bg-base)', border: '1px solid var(--cf-border)', borderRadius: 'var(--cf-radius-md)', padding: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
                  Portfolio Factor Health
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
                  <span style={{ fontSize: '22px', fontWeight: 700, color: 'var(--cf-brand-cyan)' }}>
                    {portfolioWeightedScore}
                  </span>
                  <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>/ 100</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-secondary)', marginTop: '2px' }}>
                  Capital-weighted multi-factor rating
                </div>
              </div>

              <div style={{ background: 'var(--cf-bg-base)', border: '1px solid var(--cf-border)', borderRadius: 'var(--cf-radius-md)', padding: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
                  Asset Class Allocation
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap' }}>
                  <Badge variant="neutral" size="sm">Equity: {equityPct}%</Badge>
                  <Badge variant="brand" size="sm">Crypto: {cryptoPct}%</Badge>
                  <Badge variant="warning" size="sm">ETF: {etfPct}%</Badge>
                </div>
              </div>

              <div style={{ background: 'var(--cf-bg-base)', border: '1px solid var(--cf-border)', borderRadius: 'var(--cf-radius-md)', padding: '12px' }}>
                <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
                  Volatility Dispersion
                </div>
                <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '12px', color: 'var(--cf-text-primary)', fontWeight: 600 }}>
                    {portfolioVolCounts.normal} Normal
                  </span>
                  {portfolioVolCounts.low > 0 && <span style={{ fontSize: '11px', color: 'var(--cf-brand-cyan)' }}>· {portfolioVolCounts.low} Low</span>}
                  {portfolioVolCounts.high > 0 && <span style={{ fontSize: '11px', color: 'var(--cf-warning)' }}>· {portfolioVolCounts.high} High</span>}
                  {portfolioVolCounts.extreme > 0 && <span style={{ fontSize: '11px', color: 'var(--cf-bearish)' }}>· {portfolioVolCounts.extreme} Extreme</span>}
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Positions Table */}
      <Card
        id="cf-positions-table-card"
        title={`Open Positions (${positions.length} Holdings)`}
        subtitle="Individual positions marked to market against live provider quotes"
        action={
          <button
            id="cf-btn-refresh-portfolio"
            onClick={loadPortfolios}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--cf-brand-cyan)',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ↻ Recalculate Valuations
          </button>
        }
      >
        {positions.length === 0 ? (
          <div
            id="cf-portfolio-empty-state"
            style={{
              padding: 'var(--cf-space-8)',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 'var(--cf-space-3)',
            }}
          >
            <div style={{ fontSize: '36px' }}>📊</div>
            <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--cf-text-primary)' }}>
              No holdings recorded yet
            </h3>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--cf-text-secondary)', maxWidth: '420px' }}>
              Add your current asset allocations, entry prices, and share quantities to track marked-to-market performance.
            </p>
            <button
              id="cf-btn-empty-add-pos"
              onClick={() => setIsAddPosOpen(true)}
              style={{
                marginTop: 'var(--cf-space-2)',
                background: 'var(--cf-brand-gradient)',
                color: '#ffffff',
                border: 'none',
                borderRadius: 'var(--cf-radius-md)',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              + Add First Holding
            </button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--cf-border)', color: 'var(--cf-text-muted)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>INSTRUMENT</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600 }}>CLASS</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>QUANTITY</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>AVG ENTRY</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>CURRENT PRICE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>MARKET VALUE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'right' }}>UNREALIZED P&L</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>SIGNALS & POSTURE</th>
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>ACTION</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => {
                  const pnl = Number(pos.unrealized_pnl)
                  const pnlPct = Number(pos.unrealized_pnl_percent)
                  const isUp = pnl >= 0

                  return (
                    <tr
                      key={pos.id}
                      id={`portfolio-pos-${pos.symbol}`}
                      style={{
                        borderBottom: '1px solid var(--cf-border)',
                        transition: 'background var(--cf-transition-fast)',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--cf-bg-surface-hover)')}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                    >
                      <td style={{ padding: '14px 16px' }}>
                        <div
                          onClick={() =>
                            setInspectInstrument({
                              symbol: pos.symbol,
                              name: pos.name,
                              assetType: pos.asset_type,
                              price: pos.current_price,
                            })
                          }
                          style={{
                            fontWeight: 700,
                            color: 'var(--cf-brand-cyan)',
                            cursor: 'pointer',
                            display: 'inline-block',
                          }}
                        >
                          {pos.symbol}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)' }}>{pos.name}</div>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <Badge
                          variant={pos.asset_type === 'crypto' ? 'brand' : pos.asset_type === 'etf' ? 'warning' : 'neutral'}
                          size="sm"
                        >
                          {pos.asset_type}
                        </Badge>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                        {Number(pos.quantity).toLocaleString(undefined, { maximumFractionDigits: 4 })}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', color: 'var(--cf-text-secondary)' }}>
                        ${Number(pos.average_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                        ${Number(pos.current_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                        ${Number(pos.market_value).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'right' }}>
                        <div style={{ color: isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)', fontWeight: 700 }}>
                          {isUp ? '+' : ''}${pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </div>
                        <div style={{ fontSize: '11px', color: isUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)' }}>
                          {isUp ? '+' : ''}{pnlPct.toFixed(2)}%
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <TechnicalPostureBadge
                          posture={portfolioIntelMap[pos.symbol]}
                          showScore
                          size="sm"
                          id={`portfolio-posture-${pos.symbol}`}
                        />
                      </td>
                      <td style={{ padding: '14px 16px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center' }}>
                          <button
                            id={`btn-inspect-pos-${pos.symbol}`}
                            onClick={() =>
                              setInspectInstrument({
                                symbol: pos.symbol,
                                name: pos.name,
                                assetType: pos.asset_type,
                                price: pos.current_price,
                              })
                            }
                            style={{
                              background: 'rgba(59, 130, 246, 0.12)',
                              color: 'var(--cf-brand-primary)',
                              border: '1px solid rgba(59, 130, 246, 0.25)',
                              borderRadius: 'var(--cf-radius-sm)',
                              padding: '4px 8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Inspect
                          </button>
                          <button
                            id={`btn-close-pos-${pos.symbol}`}
                            onClick={() => handleRemovePosition(pos.id, pos.symbol)}
                            title="Remove position from portfolio"
                            style={{
                              background: 'rgba(239, 68, 68, 0.12)',
                              color: 'var(--cf-bearish)',
                              border: '1px solid rgba(239, 68, 68, 0.25)',
                              borderRadius: 'var(--cf-radius-sm)',
                              padding: '4px 8px',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Remove
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Modal: Add Position */}
      {isAddPosOpen && (
        <div
          id="cf-add-pos-modal-backdrop"
          onClick={() => setIsAddPosOpen(false)}
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
            id="cf-add-pos-modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--cf-bg-surface)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-xl)',
              width: '100%',
              maxWidth: '460px',
              padding: 'var(--cf-space-6)',
              boxShadow: 'var(--cf-shadow-glass)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--cf-space-4)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--cf-text-primary)' }}>
                Add Holding to {activePortfolio?.name}
              </h3>
              <button
                onClick={() => setIsAddPosOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--cf-text-secondary)', cursor: 'pointer', fontSize: '16px' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAddPositionSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
                  INSTRUMENT SYMBOL
                </label>
                <input
                  id="cf-input-pos-symbol"
                  type="text"
                  placeholder="e.g. AAPL, BTC-USD, SPY, NVDA"
                  value={posSymbol}
                  onChange={(e) => setPosSymbol(e.target.value.toUpperCase())}
                  required
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
                  UNITS / QUANTITY HELD
                </label>
                <input
                  id="cf-input-pos-quantity"
                  type="number"
                  step="any"
                  placeholder="e.g. 10 or 0.5"
                  value={posQuantity}
                  onChange={(e) => setPosQuantity(e.target.value)}
                  required
                  min="0.00000001"
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
                  AVERAGE ACQUISITION PRICE (USD)
                </label>
                <input
                  id="cf-input-pos-price"
                  type="number"
                  step="any"
                  placeholder="e.g. 175.50"
                  value={posPrice}
                  onChange={(e) => setPosPrice(e.target.value)}
                  required
                  min="0.000001"
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--cf-space-3)' }}>
                <button
                  type="button"
                  onClick={() => setIsAddPosOpen(false)}
                  style={{
                    background: 'var(--cf-bg-surface-elevated)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    color: 'var(--cf-text-secondary)',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  id="cf-btn-submit-pos"
                  type="submit"
                  disabled={isSubmittingPos}
                  style={{
                    background: 'var(--cf-brand-gradient)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: isSubmittingPos ? 'wait' : 'pointer',
                  }}
                >
                  {isSubmittingPos ? 'Saving...' : 'Save Holding'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: New Portfolio */}
      {isNewPfOpen && (
        <div
          id="cf-new-pf-modal-backdrop"
          onClick={() => setIsNewPfOpen(false)}
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
            id="cf-new-pf-modal-content"
            onClick={(e) => e.stopPropagation()}
            style={{
              background: 'var(--cf-bg-surface)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-xl)',
              width: '100%',
              maxWidth: '440px',
              padding: 'var(--cf-space-6)',
              boxShadow: 'var(--cf-shadow-glass)',
              display: 'flex',
              flexDirection: 'column',
              gap: 'var(--cf-space-4)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: 'var(--cf-text-primary)' }}>
                Create New Portfolio
              </h3>
              <button
                onClick={() => setIsNewPfOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--cf-text-secondary)', cursor: 'pointer', fontSize: '16px' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreatePortfolio} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
                  PORTFOLIO NAME
                </label>
                <input
                  id="cf-input-pf-name"
                  type="text"
                  placeholder="e.g. Retirement IRA, Speculative Tech"
                  value={newPfName}
                  onChange={(e) => setNewPfName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-muted)', marginBottom: '4px' }}>
                  DESCRIPTION
                </label>
                <textarea
                  id="cf-input-pf-desc"
                  placeholder="Optional strategy description or investment thesis"
                  value={newPfDesc}
                  onChange={(e) => setNewPfDesc(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 12px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                    outline: 'none',
                    resize: 'none',
                  }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: 'var(--cf-space-3)' }}>
                <button
                  type="button"
                  onClick={() => setIsNewPfOpen(false)}
                  style={{
                    background: 'var(--cf-bg-surface-elevated)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    color: 'var(--cf-text-secondary)',
                    padding: '8px 14px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  id="cf-btn-submit-new-pf"
                  type="submit"
                  disabled={isSubmittingPf}
                  style={{
                    background: 'var(--cf-brand-gradient)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '8px 16px',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: isSubmittingPf ? 'wait' : 'pointer',
                  }}
                >
                  {isSubmittingPf ? 'Creating...' : 'Create Portfolio'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Asset Detail Modal for deep inspection from portfolio */}
      {inspectInstrument && (
        <AssetDetailModal
          instrument={inspectInstrument}
          intelligence={portfolioIntelMap[inspectInstrument.symbol]}
          onClose={() => setInspectInstrument(null)}
        />
      )}
    </div>
  )
}
