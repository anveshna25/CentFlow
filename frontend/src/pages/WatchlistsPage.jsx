import { useState, useEffect, useCallback } from 'react'
import { Card, Badge, LoadingState, ErrorState, EmptyState } from '../components/common'
import { useNavigation } from '../state/NavigationContext'
import { PAGES } from '../state/pages'
import {
  getWatchlists,
  getWatchlist,
  createWatchlist,
  deleteWatchlist,
  addToWatchlist,
  removeFromWatchlist,
} from '../api/watchlist'

const POPULAR_SUGGESTIONS = ['AAPL', 'MSFT', 'NVDA', 'BTC-USD', 'ETH-USD', 'SPY']

export function WatchlistsPage() {
  const { navigate } = useNavigation()

  // State
  const [watchlists, setWatchlists] = useState([])
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(null)
  const [activeWatchlist, setActiveWatchlist] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDetailLoading, setIsDetailLoading] = useState(false)
  const [error, setError] = useState(null)

  // Actions state
  const [symbolInput, setSymbolInput] = useState('')
  const [isAdding, setIsAdding] = useState(false)
  const [feedback, setFeedback] = useState(null) // { type: 'success' | 'info' | 'error', message: '' }
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

  // Handle adding symbol
  const handleAddSymbol = async (symbolToAdd) => {
    const symbol = (symbolToAdd || symbolInput).trim().toUpperCase()
    if (!symbol || !activeWatchlist) return

    // Client-side quick duplicate check
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
        // Refresh watchlist
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

  // Handle removing symbol
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

  // Format monetary value
  const formatPrice = (val, currency = 'USD') => {
    if (val === null || val === undefined) return '—'
    const num = Number(val)
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency || 'USD',
      minimumFractionDigits: num >= 100 ? 2 : 2,
    }).format(num)
  }

  // Format 24h change
  const formatChange = (pct) => {
    if (pct === null || pct === undefined) return null
    const num = Number(pct)
    const sign = num > 0 ? '+' : ''
    return `${sign}${num.toFixed(2)}%`
  }

  return (
    <div id="cf-watchlists-page" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-6)' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 'var(--cf-space-4)' }}>
        <div>
          <h1 style={{ fontSize: '26px', margin: 0, letterSpacing: '-0.02em' }}>Watchlists</h1>
          <p style={{ color: 'var(--cf-text-secondary)', margin: '4px 0 0', fontSize: '14px' }}>
            Monitor and track high-conviction market instruments with persistent live prices.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--cf-space-3)' }}>
          <button
            id="cf-new-watchlist-btn"
            onClick={() => setShowCreateModal(true)}
            style={{
              background: 'var(--cf-bg-surface-elevated)',
              color: 'var(--cf-text-primary)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '9px 16px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>+</span> New Watchlist
          </button>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <ErrorState
          error={error}
          compact
          onRetry={loadWatchlists}
          id="cf-watchlist-error"
        />
      )}

      {/* Action Feedback Banner */}
      {feedback && (
        <div
          id="cf-watchlist-feedback"
          style={{
            padding: '10px 16px',
            borderRadius: 'var(--cf-radius-md)',
            fontSize: '13px',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
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
          <span>{feedback.message}</span>
          <button
            onClick={() => setFeedback(null)}
            style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '14px' }}
          >
            ✕
          </button>
        </div>
      )}

      {/* Create Watchlist Modal / Inline Panel */}
      {showCreateModal && (
        <Card id="cf-create-watchlist-card" title="Create New Watchlist" subtitle="Group instruments into a dedicated tracking collection">
          <form onSubmit={handleCreateWatchlist} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-4)' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '6px' }}>
                WATCHLIST NAME *
              </label>
              <input
                id="cf-watchlist-name-input"
                type="text"
                placeholder="e.g. Dividend Blue Chips, Layer 1 Blockchains..."
                value={newWatchlistName}
                onChange={(e) => setNewWatchlistName(e.target.value)}
                required
                style={{
                  width: '100%',
                  background: 'var(--cf-bg-base)',
                  border: '1px solid var(--cf-border)',
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '10px 14px',
                  color: 'var(--cf-text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', marginBottom: '6px' }}>
                DESCRIPTION (OPTIONAL)
              </label>
              <input
                id="cf-watchlist-desc-input"
                type="text"
                placeholder="Investment thesis or category description..."
                value={newWatchlistDesc}
                onChange={(e) => setNewWatchlistDesc(e.target.value)}
                style={{
                  width: '100%',
                  background: 'var(--cf-bg-base)',
                  border: '1px solid var(--cf-border)',
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '10px 14px',
                  color: 'var(--cf-text-primary)',
                  fontSize: '14px',
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: 'var(--cf-space-3)', justifyContent: 'flex-end', marginTop: 'var(--cf-space-2)' }}>
              <button
                type="button"
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
                id="cf-submit-create-watchlist-btn"
                type="submit"
                style={{
                  background: 'var(--cf-brand-gradient)',
                  border: 'none',
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '8px 18px',
                  color: '#ffffff',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Create Watchlist
              </button>
            </div>
          </form>
        </Card>
      )}

      {/* Watchlist Tabs Bar */}
      {watchlists.length > 0 && (
        <div style={{ display: 'flex', gap: 'var(--cf-space-2)', overflowX: 'auto', paddingBottom: '4px' }}>
          {watchlists.map((wl) => {
            const isActive = wl.id === selectedWatchlistId
            return (
              <button
                key={wl.id}
                id={`cf-wl-tab-${wl.id}`}
                onClick={() => setSelectedWatchlistId(wl.id)}
                style={{
                  background: isActive ? 'var(--cf-brand-primary)' : 'var(--cf-bg-surface-elevated)',
                  color: isActive ? '#ffffff' : 'var(--cf-text-secondary)',
                  border: `1px solid ${isActive ? 'var(--cf-brand-primary)' : 'var(--cf-border)'}`,
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '8px 16px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  whiteSpace: 'nowrap',
                  transition: 'all var(--cf-transition-fast)',
                }}
              >
                <span>{wl.name}</span>
                <span
                  style={{
                    background: isActive ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.06)',
                    padding: '2px 7px',
                    borderRadius: 'var(--cf-radius-full)',
                    fontSize: '11px',
                  }}
                >
                  {wl.items_count}
                </span>
              </button>
            )
          })}
        </div>
      )}

      {/* Quick Add Asset Bar */}
      {activeWatchlist && (
        <Card id="cf-add-asset-bar" style={{ padding: 'var(--cf-space-4)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-3)' }}>
            <div style={{ display: 'flex', gap: 'var(--cf-space-3)', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '220px', display: 'flex', gap: '8px' }}>
                <input
                  id="cf-watchlist-add-input"
                  type="text"
                  placeholder="Enter ticker symbol (e.g. AAPL, NVDA, BTC-USD)..."
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      handleAddSymbol()
                    }
                  }}
                  style={{
                    flex: 1,
                    background: 'var(--cf-bg-base)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 14px',
                    color: 'var(--cf-text-primary)',
                    fontSize: '13px',
                  }}
                />
                <button
                  id="cf-watchlist-add-btn"
                  onClick={() => handleAddSymbol()}
                  disabled={isAdding || !symbolInput.trim()}
                  style={{
                    background: 'var(--cf-brand-gradient)',
                    border: 'none',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 20px',
                    color: '#ffffff',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: isAdding || !symbolInput.trim() ? 'not-allowed' : 'pointer',
                    opacity: isAdding || !symbolInput.trim() ? 0.6 : 1,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {isAdding ? 'Adding...' : '+ Add Asset'}
                </button>
              </div>

              {watchlists.length > 1 && (
                <button
                  id="cf-delete-watchlist-btn"
                  onClick={handleDeleteWatchlist}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--cf-bearish-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '10px 14px',
                    color: 'var(--cf-bearish)',
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  Delete Watchlist
                </button>
              )}
            </div>

            {/* Quick Suggestion Pills */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '11px', color: 'var(--cf-text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                Quick Add:
              </span>
              {POPULAR_SUGGESTIONS.map((sym) => {
                const isTracked = activeWatchlist.items.some(
                  (i) => i.symbol.toUpperCase() === sym.toUpperCase()
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
                  <th style={{ padding: '12px 16px', fontWeight: 600, textAlign: 'center' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {activeWatchlist.items.map((item) => {
                  const changeText = formatChange(item.change_pct)
                  const isUp = item.is_up ?? (item.change >= 0)

                  return (
                    <tr
                      key={item.id}
                      id={`watchlist-row-${item.symbol}`}
                      style={{
                        borderBottom: '1px solid rgba(255, 255, 255, 0.04)',
                        transition: 'background var(--cf-transition-fast)',
                      }}
                      onMouseOver={(e) => (e.currentTarget.style.background = 'var(--cf-bg-surface-hover)')}
                      onMouseOut={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                            {item.symbol}
                          </span>
                          <span style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
                            {item.currency}
                          </span>
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--cf-text-secondary)', marginTop: '2px' }}>
                          {item.name}
                        </div>
                      </td>

                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant="neutral" size="sm">
                          {item.asset_type || 'Equity'}
                        </Badge>
                      </td>

                      <td style={{ padding: '14px 16px', color: 'var(--cf-text-secondary)', fontSize: '12px' }}>
                        {item.exchange || 'Market'}
                      </td>

                      <td style={{ padding: '14px 16px', textAlign: 'right', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
                        {formatPrice(item.price, item.currency)}
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
                        <div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          <button
                            id={`cf-open-chart-${item.symbol}`}
                            onClick={() => navigate(PAGES.MARKETS, { symbol: item.symbol })}
                            style={{
                              background: 'var(--cf-bg-surface-elevated)',
                              border: '1px solid var(--cf-border)',
                              borderRadius: 'var(--cf-radius-sm)',
                              padding: '5px 12px',
                              color: 'var(--cf-brand-primary)',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            Open Chart →
                          </button>
                          <button
                            id={`cf-remove-item-${item.symbol}`}
                            onClick={() => handleRemoveSymbol(item.symbol)}
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
    </div>
  )
}
