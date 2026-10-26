import { useState, useEffect, useRef, useCallback } from 'react'
import { Badge } from '../common/Badge'
import { searchInstruments } from '../../api/marketData'
import { highlightMatch } from '../../utils/highlight'
import { useNavigation } from '../../state/NavigationContext'
import { PAGES } from '../../state/pages'
import { useTheme } from '../../state/ThemeContext'

// Fallback catalog in case backend search is offline or loading
const FALLBACK_CATALOG = [
  { symbol: 'AAPL', name: 'Apple Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities' },
  { symbol: 'NVDA', name: 'NVIDIA Corporation', assetType: 'equity', exchange: 'NASDAQ', market: 'US Equities' },
  { symbol: 'BTC-USD', name: 'Bitcoin USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto' },
  { symbol: 'ETH-USD', name: 'Ethereum USD', assetType: 'crypto', exchange: 'Coinbase', market: 'Crypto' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF Trust', assetType: 'etf', exchange: 'NYSE', market: 'US ETFs' },
  { symbol: 'QQQ', name: 'Invesco QQQ Trust (Nasdaq 100)', assetType: 'etf', exchange: 'NASDAQ', market: 'US ETFs' },
]

export function Header({ onSearch, searchValue = '', onSelectAsset }) {
  const { navigate } = useNavigation()
  const { isDark, toggleTheme } = useTheme()
  const [query, setQuery] = useState(searchValue)
  const [prevSearchValue, setPrevSearchValue] = useState(searchValue)
  const [results, setResults] = useState([])
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [isFocused, setIsFocused] = useState(false)

  const containerRef = useRef(null)
  const inputRef = useRef(null)

  // Adjust local query when external searchValue prop changes
  if (searchValue !== prevSearchValue) {
    setPrevSearchValue(searchValue)
    setQuery(searchValue)
  }

  // Debounced API search
  useEffect(() => {
    const trimmed = query.trim()
    if (!trimmed) return

    const timer = setTimeout(async () => {
      setIsLoading(true)
      setIsOpen(true)
      try {
        const res = await searchInstruments(trimmed)
        if (res?.data && res.data.length > 0) {
          const normalized = res.data.map((item) => ({
            symbol: item.symbol,
            name: item.name,
            assetType: item.asset_type || item.assetType || 'equity',
            exchange: item.exchange || 'N/A',
            market: item.market || 'Global',
            currency: item.currency || 'USD',
          }))
          setResults(normalized)
        } else {
          // If backend returns empty, filter fallback catalog
          const localMatches = FALLBACK_CATALOG.filter(
            (item) =>
              item.symbol.toLowerCase().includes(trimmed.toLowerCase()) ||
              item.name.toLowerCase().includes(trimmed.toLowerCase()) ||
              item.assetType.toLowerCase().includes(trimmed.toLowerCase())
          )
          setResults(localMatches)
        }
      } catch {
        // Fallback to local catalog on error
        const localMatches = FALLBACK_CATALOG.filter(
          (item) =>
            item.symbol.toLowerCase().includes(trimmed.toLowerCase()) ||
            item.name.toLowerCase().includes(trimmed.toLowerCase())
        )
        setResults(localMatches)
      } finally {
        setIsLoading(false)
      }
    }, 250)

    return () => clearTimeout(timer)
  }, [query])

  // Global hotkey: Ctrl+K / Cmd+K or '/' to focus search
  useEffect(() => {
    const handleKeyDown = (e) => {
      const isInput = ['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
        inputRef.current?.select()
      } else if (e.key === '/' && !isInput) {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = useCallback((item) => {
    setIsOpen(false)
    setSelectedIndex(-1)
    if (onSelectAsset) {
      onSelectAsset(item)
    } else {
      navigate(PAGES.MARKETS, { symbol: item.symbol })
    }
  }, [onSelectAsset, navigate])

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!isOpen && results.length > 0) {
        setIsOpen(true)
        setSelectedIndex(0)
      } else if (results.length > 0) {
        setSelectedIndex((prev) => (prev + 1) % results.length)
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (results.length > 0) {
        setSelectedIndex((prev) => (prev <= 0 ? results.length - 1 : prev - 1))
      }
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (selectedIndex >= 0 && results[selectedIndex]) {
        handleSelect(results[selectedIndex])
      } else if (results.length > 0) {
        handleSelect(results[0])
      } else if (query.trim()) {
        // Navigate to markets page with search query
        setIsOpen(false)
        onSearch?.(query.trim())
        navigate(PAGES.MARKETS, { search: query.trim() })
      }
    } else if (e.key === 'Escape') {
      e.preventDefault()
      setIsOpen(false)
      inputRef.current?.blur()
    }
  }

  const handleClear = () => {
    setQuery('')
    setResults([])
    setIsOpen(false)
    setSelectedIndex(-1)
    onSearch?.('')
    inputRef.current?.focus()
  }

  const handleChange = (e) => {
    const val = e.target.value
    setQuery(val)
    if (!val.trim()) {
      setResults([])
      setIsOpen(false)
      setIsLoading(false)
      setSelectedIndex(-1)
    }
    onSearch?.(val)
  }

  return (
    <header
      id="cf-global-header"
      style={{
        height: '64px',
        borderBottom: '1px solid var(--cf-border)',
        background: 'var(--cf-bg-header)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--cf-space-6)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Global Asset Search Bar & Autocomplete Dropdown */}
      <div
        ref={containerRef}
        id="cf-global-search-container"
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: '440px',
        }}
      >
        <div
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            width: '100%',
          }}
        >
          {/* Search Icon */}
          <span
            style={{
              position: 'absolute',
              left: '14px',
              color: isFocused ? 'var(--cf-brand-cyan)' : 'var(--cf-text-muted)',
              display: 'flex',
              alignItems: 'center',
              pointerEvents: 'none',
              transition: 'color var(--cf-transition-fast)',
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </span>

          <input
            ref={inputRef}
            id="cf-search-input"
            type="search"
            role="combobox"
            aria-expanded={isOpen}
            aria-autocomplete="list"
            aria-controls="cf-search-results-list"
            aria-label="Search financial assets and markets"
            placeholder="Search assets, symbols, markets... (Ctrl+K)"
            value={query}
            onChange={handleChange}
            onFocus={() => {
              setIsFocused(true)
              if (query.trim() && results.length > 0) setIsOpen(true)
            }}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            style={{
              width: '100%',
              background: 'var(--cf-bg-surface-elevated)',
              border: `1px solid ${isFocused ? 'var(--cf-brand-primary)' : 'var(--cf-border)'}`,
              borderRadius: 'var(--cf-radius-full)',
              padding: '9px 72px 9px 38px',
              color: 'var(--cf-text-primary)',
              fontSize: '13px',
              outline: 'none',
              boxShadow: isFocused ? '0 0 14px rgba(0, 102, 255, 0.25)' : 'none',
              transition: 'all var(--cf-transition-fast)',
            }}
          />

          {/* Right Controls: Spinner / Clear / Hotkey Hint */}
          <div
            style={{
              position: 'absolute',
              right: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            {isLoading && (
              <span
                style={{
                  width: '13px',
                  height: '13px',
                  borderRadius: '50%',
                  border: '2px solid rgba(0, 229, 255, 0.2)',
                  borderTopColor: 'var(--cf-brand-cyan)',
                  animation: 'cf-spin 0.6s linear infinite',
                  display: 'inline-block',
                }}
              />
            )}

            {query && !isLoading && (
              <button
                type="button"
                id="cf-search-clear-btn"
                onClick={handleClear}
                aria-label="Clear search query"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--cf-text-muted)',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: '12px',
                }}
              >
                ✕
              </button>
            )}

            {!query && !isFocused && (
              <span
                style={{
                  fontSize: '10px',
                  fontFamily: 'var(--cf-font-mono)',
                  color: 'var(--cf-text-muted)',
                  background: 'var(--cf-bg-base)',
                  border: '1px solid var(--cf-border)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  pointerEvents: 'none',
                }}
              >
                Ctrl K
              </span>
            )}
          </div>
        </div>

        {/* Search Results Dropdown */}
        {isOpen && query.trim().length > 0 && (
          <div
            id="cf-search-results-dropdown"
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              left: 0,
              right: 0,
              background: 'var(--cf-bg-surface-elevated)',
              border: '1px solid var(--cf-border-glow)',
              borderRadius: 'var(--cf-radius-lg)',
              boxShadow: 'var(--cf-shadow-glass)',
              backdropFilter: 'blur(16px)',
              overflow: 'hidden',
              zIndex: 100,
              maxHeight: '380px',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Dropdown Header */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 14px',
                borderBottom: '1px solid var(--cf-border)',
                background: 'rgba(0, 0, 0, 0.25)',
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--cf-text-muted)',
              }}
            >
              <span>
                {isLoading
                  ? 'SEARCHING CATALOG...'
                  : `MATCHING INSTRUMENTS (${results.length})`}
              </span>
              <span style={{ fontSize: '10px' }}>
                ↑↓ Navigate • Enter Select • Esc Close
              </span>
            </div>

            {/* Results List */}
            {results.length > 0 ? (
              <ul
                id="cf-search-results-list"
                role="listbox"
                style={{
                  listStyle: 'none',
                  margin: 0,
                  padding: '4px 0',
                  overflowY: 'auto',
                  maxHeight: '320px',
                }}
              >
                {results.map((item, index) => {
                  const isSelected = selectedIndex === index
                  const badgeVariant =
                    item.assetType === 'crypto'
                      ? 'brand'
                      : item.assetType === 'etf'
                        ? 'warning'
                        : 'neutral'

                  return (
                    <li
                      key={item.symbol}
                      id={`cf-search-result-${item.symbol}`}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setSelectedIndex(index)}
                      style={{
                        padding: '10px 14px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        cursor: 'pointer',
                        background: isSelected
                          ? 'var(--cf-bg-surface-hover)'
                          : 'transparent',
                        borderLeft: `3px solid ${isSelected ? 'var(--cf-brand-cyan)' : 'transparent'}`,
                        transition: 'all var(--cf-transition-fast)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                        <span
                          style={{
                            fontFamily: 'var(--cf-font-mono)',
                            fontWeight: 700,
                            fontSize: '13px',
                            color: 'var(--cf-brand-cyan)',
                            minWidth: '65px',
                          }}
                        >
                          {highlightMatch(item.symbol, query)}
                        </span>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          <div
                            style={{
                              fontSize: '13px',
                              color: 'var(--cf-text-primary)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {highlightMatch(item.name, query)}
                          </div>
                          <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>
                            {item.exchange} • {item.market || 'Global'}
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                        <Badge variant={badgeVariant} size="sm">
                          {item.assetType}
                        </Badge>
                        <span
                          style={{
                            fontSize: '11px',
                            color: isSelected ? 'var(--cf-brand-cyan)' : 'var(--cf-text-muted)',
                            fontWeight: 600,
                          }}
                        >
                          Inspect ↗
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            ) : !isLoading ? (
              <div
                id="cf-search-empty-state"
                style={{
                  padding: 'var(--cf-space-6) var(--cf-space-4)',
                  textAlign: 'center',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <div style={{ color: 'var(--cf-text-muted)', fontSize: '24px' }}>🔍</div>
                <div style={{ color: 'var(--cf-text-primary)', fontSize: '13px', fontWeight: 600 }}>
                  No instruments found for &ldquo;{query}&rdquo;
                </div>
                <div style={{ color: 'var(--cf-text-muted)', fontSize: '12px', maxWidth: '300px' }}>
                  Try searching by ticker (AAPL, BTC-USD, SPY) or company name.
                </div>
                <button
                  type="button"
                  id="cf-search-fallback-btn"
                  onClick={() => {
                    setIsOpen(false)
                    onSearch?.(query)
                    navigate(PAGES.MARKETS, { search: query })
                  }}
                  style={{
                    marginTop: '4px',
                    background: 'var(--cf-bg-surface)',
                    border: '1px solid var(--cf-border)',
                    borderRadius: 'var(--cf-radius-md)',
                    padding: '6px 12px',
                    color: 'var(--cf-brand-cyan)',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Explore in Markets Directory →
                </button>
              </div>
            ) : null}
          </div>
        )}
      </div>

      {/* Right Status Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--cf-bullish)',
              boxShadow: '0 0 8px var(--cf-bullish)',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: '12px', color: 'var(--cf-text-secondary)', fontWeight: 500 }}>
            Market Data: Connected
          </span>
        </div>

        <Badge variant="brand" size="sm">
          Core Engine v0.1.0
        </Badge>

        <button
          id="cf-theme-toggle"
          onClick={toggleTheme}
          title={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
          aria-label={`Switch to ${isDark ? 'Light' : 'Dark'} mode`}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '32px',
            height: '32px',
            borderRadius: 'var(--cf-radius-md)',
            background: 'var(--cf-bg-surface-elevated)',
            border: '1px solid var(--cf-border)',
            color: 'var(--cf-text-secondary)',
            cursor: 'pointer',
            fontSize: '14px',
            transition: 'all var(--cf-transition-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--cf-border-hover)'
            e.currentTarget.style.color = 'var(--cf-text-primary)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--cf-border)'
            e.currentTarget.style.color = 'var(--cf-text-secondary)'
          }}
        >
          {isDark ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  )
}
