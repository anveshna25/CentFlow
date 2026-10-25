import { useState, useRef, useEffect, useMemo, useCallback } from 'react'

/**
 * Interactive PriceChart component supporting Line and Candlestick modes,
 * customizable timeframes, volume histogram, and hover crosshair with tooltip.
 */
export function PriceChart({
  data = [],
  symbol = '',
  currency = 'USD',
  isLoading = false,
  timeframe = '1M',
  onTimeframeChange,
  height = 360,
  id = 'cf-price-chart',
}) {
  const containerRef = useRef(null)
  const [containerWidth, setContainerWidth] = useState(600)
  const [chartType, setChartType] = useState('line') // 'line' | 'candles'
  const [hoverIndex, setHoverIndex] = useState(null)

  // Measure container width responsively
  useEffect(() => {
    if (!containerRef.current) return
    const el = containerRef.current
    const updateWidth = () => {
      if (el.clientWidth) {
        setContainerWidth(Math.max(320, el.clientWidth))
      }
    }
    updateWidth()

    const observer = new ResizeObserver(updateWidth)
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Geometry dimensions
  const padding = { top: 24, right: 65, bottom: 44, left: 16 }
  const plotWidth = Math.max(100, containerWidth - padding.left - padding.right)
  const pricePlotHeight = Math.max(80, height * 0.65 - padding.top)
  const volumePlotHeight = Math.max(20, height * 0.18)
  const volumeTop = padding.top + pricePlotHeight + 14

  // Process and sort bars by timestamp
  const sortedBars = useMemo(() => {
    if (!data || data.length === 0) return []
    return [...data].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
  }, [data])

  // Price & Volume ranges
  const { minPrice, maxPrice, maxVolume, isNetUp } = useMemo(() => {
    if (sortedBars.length === 0) {
      return { minPrice: 0, maxPrice: 100, maxVolume: 1, isNetUp: true }
    }
    let minP = Number.POSITIVE_INFINITY
    let maxP = Number.NEGATIVE_INFINITY
    let maxV = 0

    for (const b of sortedBars) {
      const low = Number(b.low ?? b.close ?? 0)
      const high = Number(b.high ?? b.close ?? 0)
      const vol = Number(b.volume ?? 0)
      if (low < minP) minP = low
      if (high > maxP) maxP = high
      if (vol > maxV) maxV = vol
    }

    if (minP === maxP) {
      minP *= 0.95
      maxP *= 1.05
    } else {
      const margin = (maxP - minP) * 0.05
      minP = Math.max(0, minP - margin)
      maxP += margin
    }

    const first = sortedBars[0]
    const last = sortedBars[sortedBars.length - 1]
    const netUp = Number(last.close ?? last.price ?? 0) >= Number(first.open ?? first.price ?? 0)

    return {
      minPrice: minP,
      maxPrice: maxP,
      maxVolume: maxV || 1,
      isNetUp: netUp,
    }
  }, [sortedBars])

  // Coordinate mappers
  const getY = useCallback(
    (price) => {
      const p = Number(price)
      const ratio = (p - minPrice) / (maxPrice - minPrice || 1)
      return padding.top + pricePlotHeight - ratio * pricePlotHeight
    },
    [minPrice, maxPrice, padding.top, pricePlotHeight]
  )

  const getX = useCallback(
    (index) => {
      if (sortedBars.length <= 1) return padding.left + plotWidth / 2
      return padding.left + (index / (sortedBars.length - 1)) * plotWidth
    },
    [sortedBars.length, padding.left, plotWidth]
  )

  const getVolY = useCallback(
    (vol) => {
      const v = Number(vol)
      const h = (v / maxVolume) * volumePlotHeight
      return volumeTop + volumePlotHeight - h
    },
    [maxVolume, volumePlotHeight, volumeTop]
  )

  // Generate SVG path for line and area gradient
  const { linePath, areaPath } = useMemo(() => {
    if (sortedBars.length === 0) return { linePath: '', areaPath: '' }

    const points = sortedBars.map((b, idx) => {
      const x = getX(idx)
      const y = getY(b.close ?? b.price)
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })

    const lPath = `M ${points.join(' L ')}`
    const lastX = getX(sortedBars.length - 1)
    const firstX = getX(0)
    const baseY = padding.top + pricePlotHeight
    const aPath = `${lPath} L ${lastX.toFixed(1)},${baseY} L ${firstX.toFixed(1)},${baseY} Z`

    return { linePath: lPath, areaPath: aPath }
  }, [sortedBars, getX, getY, padding.top, pricePlotHeight])

  // Interactive mouse move for crosshair
  const handleMouseMove = (e) => {
    if (!sortedBars.length) return
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left

    const clampedX = Math.max(padding.left, Math.min(padding.left + plotWidth, mouseX))
    const ratio = (clampedX - padding.left) / (plotWidth || 1)
    const idx = Math.round(ratio * (sortedBars.length - 1))
    setHoverIndex(Math.max(0, Math.min(sortedBars.length - 1, idx)))
  }

  const handleMouseLeave = () => {
    setHoverIndex(null)
  }

  // Active bar under crosshair or latest bar
  const activeBar = hoverIndex !== null ? sortedBars[hoverIndex] : sortedBars[sortedBars.length - 1]
  const themeColor = isNetUp ? 'var(--cf-bullish)' : 'var(--cf-bearish)'
  const candleWidth = Math.max(3, Math.min(14, (plotWidth / (sortedBars.length || 1)) * 0.65))

  // Timeframe buttons
  const timeframes = ['1D', '1W', '1M', '1Y', 'ALL']

  return (
    <div
      id={id}
      ref={containerRef}
      style={{
        background: 'var(--cf-bg-surface-elevated)',
        border: '1px solid var(--cf-border)',
        borderRadius: 'var(--cf-radius-lg)',
        padding: 'var(--cf-space-4)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--cf-space-3)',
        position: 'relative',
      }}
    >
      {/* Chart Header: Title, Price Summary & View Controls */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 'var(--cf-space-3)',
          borderBottom: '1px solid var(--cf-border)',
          paddingBottom: 'var(--cf-space-3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 'var(--cf-space-3)' }}>
          <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
            {symbol}
          </span>
          {activeBar && (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
              <span style={{ fontSize: '20px', fontWeight: 800, color: 'var(--cf-text-primary)', letterSpacing: '-0.02em' }}>
                ${Number(activeBar.close ?? activeBar.price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>{currency}</span>
              {activeBar.open && activeBar.close && (
                <span
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: Number(activeBar.close) >= Number(activeBar.open) ? 'var(--cf-bullish)' : 'var(--cf-bearish)',
                  }}
                >
                  {Number(activeBar.close) >= Number(activeBar.open) ? '+' : ''}
                  {(Number(activeBar.close) - Number(activeBar.open)).toFixed(2)} (
                  {(((Number(activeBar.close) - Number(activeBar.open)) / Number(activeBar.open)) * 100).toFixed(2)}%)
                </span>
              )}
            </div>
          )}
        </div>

        {/* View & Timeframe Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)', flexWrap: 'wrap' }}>
          {/* Chart Type Toggle */}
          <div
            style={{
              display: 'inline-flex',
              background: 'var(--cf-bg-base)',
              padding: '2px',
              borderRadius: 'var(--cf-radius-md)',
              border: '1px solid var(--cf-border)',
            }}
          >
            <button
              id={`${id}-btn-line`}
              onClick={() => setChartType('line')}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--cf-radius-sm)',
                fontSize: '11px',
                fontWeight: 600,
                background: chartType === 'line' ? 'var(--cf-brand-primary)' : 'transparent',
                color: chartType === 'line' ? '#ffffff' : 'var(--cf-text-secondary)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              Line
            </button>
            <button
              id={`${id}-btn-candles`}
              onClick={() => setChartType('candles')}
              style={{
                padding: '4px 10px',
                borderRadius: 'var(--cf-radius-sm)',
                fontSize: '11px',
                fontWeight: 600,
                background: chartType === 'candles' ? 'var(--cf-brand-primary)' : 'transparent',
                color: chartType === 'candles' ? '#ffffff' : 'var(--cf-text-secondary)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all var(--cf-transition-fast)',
              }}
            >
              Candles
            </button>
          </div>

          {/* Timeframe Buttons */}
          <div
            style={{
              display: 'inline-flex',
              background: 'var(--cf-bg-base)',
              padding: '2px',
              borderRadius: 'var(--cf-radius-md)',
              border: '1px solid var(--cf-border)',
            }}
          >
            {timeframes.map((tf) => (
              <button
                key={tf}
                id={`${id}-tf-${tf.toLowerCase()}`}
                onClick={() => onTimeframeChange && onTimeframeChange(tf)}
                style={{
                  padding: '4px 10px',
                  borderRadius: 'var(--cf-radius-sm)',
                  fontSize: '11px',
                  fontWeight: 600,
                  background: timeframe === tf ? 'var(--cf-brand-cyan)' : 'transparent',
                  color: timeframe === tf ? 'var(--cf-text-inverse)' : 'var(--cf-text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  transition: 'all var(--cf-transition-fast)',
                }}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main SVG Area */}
      <div style={{ position: 'relative', width: '100%', height: `${height}px` }}>
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'rgba(17, 24, 39, 0.7)',
              backdropFilter: 'blur(4px)',
              zIndex: 10,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 'var(--cf-radius-md)',
              color: 'var(--cf-brand-cyan)',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            Loading historical data...
          </div>
        )}

        {sortedBars.length === 0 && !isLoading ? (
          <div
            style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--cf-text-muted)',
              fontSize: '13px',
            }}
          >
            No historical price bars available for {symbol}.
          </div>
        ) : (
          <svg
            id={`${id}-svg`}
            width="100%"
            height={height}
            style={{ display: 'block', overflow: 'visible', cursor: 'crosshair' }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
          >
            <defs>
              <linearGradient id={`${id}-gradient`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={themeColor} stopOpacity="0.25" />
                <stop offset="100%" stopColor={themeColor} stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Horizontal Grid Lines & Price Labels */}
            {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
              const y = padding.top + pricePlotHeight * (1 - r)
              const priceVal = minPrice + (maxPrice - minPrice) * r
              return (
                <g key={i}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={padding.left + plotWidth}
                    y2={y}
                    stroke="rgba(255, 255, 255, 0.06)"
                    strokeDasharray="4 4"
                    strokeWidth="1"
                  />
                  <text
                    x={padding.left + plotWidth + 8}
                    y={y + 4}
                    fill="var(--cf-text-muted)"
                    fontSize="10"
                    fontFamily="var(--cf-font-sans)"
                  >
                    ${priceVal.toFixed(priceVal >= 100 ? 1 : 2)}
                  </text>
                </g>
              )
            })}

            {/* Volume Separator Line */}
            <line
              x1={padding.left}
              y1={volumeTop - 4}
              x2={padding.left + plotWidth}
              y2={volumeTop - 4}
              stroke="rgba(255, 255, 255, 0.08)"
              strokeWidth="1"
            />
            <text
              x={padding.left + plotWidth + 8}
              y={volumeTop + 10}
              fill="var(--cf-text-muted)"
              fontSize="9"
              fontFamily="var(--cf-font-sans)"
            >
              Vol
            </text>

            {/* Volume Bars */}
            {sortedBars.map((b, idx) => {
              const x = getX(idx)
              const y = getVolY(b.volume)
              const barH = volumeTop + volumePlotHeight - y
              const barColor = Number(b.close) >= Number(b.open) ? 'rgba(16, 185, 129, 0.35)' : 'rgba(239, 68, 68, 0.35)'
              const bWidth = Math.max(1, candleWidth * 0.8)
              return (
                <rect
                  key={`vol-${idx}`}
                  x={x - bWidth / 2}
                  y={y}
                  width={bWidth}
                  height={Math.max(1, barH)}
                  fill={barColor}
                  rx="1"
                />
              )
            })}

            {/* Chart Mode: Line */}
            {chartType === 'line' && (
              <>
                <path d={areaPath} fill={`url(#${id}-gradient)`} />
                <path
                  d={linePath}
                  fill="none"
                  stroke={themeColor}
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </>
            )}

            {/* Chart Mode: Candlesticks */}
            {chartType === 'candles' &&
              sortedBars.map((b, idx) => {
                const x = getX(idx)
                const openY = getY(b.open ?? b.close)
                const closeY = getY(b.close)
                const highY = getY(b.high ?? Math.max(b.open, b.close))
                const lowY = getY(b.low ?? Math.min(b.open, b.close))
                const isBull = Number(b.close) >= Number(b.open)
                const color = isBull ? 'var(--cf-bullish)' : 'var(--cf-bearish)'

                const bodyTop = Math.min(openY, closeY)
                const bodyHeight = Math.max(2, Math.abs(closeY - openY))

                return (
                  <g key={`candle-${idx}`}>
                    {/* Upper & Lower Wicks */}
                    <line
                      x1={x}
                      y1={highY}
                      x2={x}
                      y2={lowY}
                      stroke={color}
                      strokeWidth="1.2"
                    />
                    {/* Candle Body */}
                    <rect
                      x={x - candleWidth / 2}
                      y={bodyTop}
                      width={candleWidth}
                      height={bodyHeight}
                      fill={color}
                      rx="1"
                    />
                  </g>
                )
              })}

            {/* Time Axis Date Labels (approx 5 labels across range) */}
            {sortedBars.length > 0 &&
              [0, 0.25, 0.5, 0.75, 1].map((r, i) => {
                const idx = Math.min(sortedBars.length - 1, Math.round(r * (sortedBars.length - 1)))
                const bar = sortedBars[idx]
                if (!bar) return null
                const x = getX(idx)
                const dateStr = new Date(bar.timestamp).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })
                return (
                  <text
                    key={`label-${i}`}
                    x={x}
                    y={height - 6}
                    textAnchor="middle"
                    fill="var(--cf-text-muted)"
                    fontSize="10"
                    fontFamily="var(--cf-font-sans)"
                  >
                    {dateStr}
                  </text>
                )
              })}

            {/* Interactive Crosshair & Tooltip Indicator */}
            {hoverIndex !== null && sortedBars[hoverIndex] && (
              (() => {
                const hBar = sortedBars[hoverIndex]
                const hX = getX(hoverIndex)
                const hY = getY(hBar.close ?? hBar.price)

                return (
                  <g>
                    {/* Vertical Crosshair Line */}
                    <line
                      x1={hX}
                      y1={padding.top}
                      x2={hX}
                      y2={volumeTop + volumePlotHeight}
                      stroke="rgba(255, 255, 255, 0.35)"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    {/* Horizontal Price Crosshair Line */}
                    <line
                      x1={padding.left}
                      y1={hY}
                      x2={padding.left + plotWidth}
                      y2={hY}
                      stroke="rgba(255, 255, 255, 0.35)"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    {/* Point Marker */}
                    <circle
                      cx={hX}
                      cy={hY}
                      r="4.5"
                      fill={themeColor}
                      stroke="#ffffff"
                      strokeWidth="2"
                    />
                  </g>
                )
              })()
            )}
          </svg>
        )}

        {/* Hover Crosshair Floating Tooltip */}
        {hoverIndex !== null && sortedBars[hoverIndex] && (
          (() => {
            const hBar = sortedBars[hoverIndex]
            const hX = getX(hoverIndex)
            const isLeft = hX < containerWidth / 2

            return (
              <div
                style={{
                  position: 'absolute',
                  top: '12px',
                  ...(isLeft ? { left: `${hX + 16}px` } : { right: `${containerWidth - hX + 16}px` }),
                  background: 'var(--cf-bg-surface-glass)',
                  backdropFilter: 'blur(10px)',
                  border: '1px solid var(--cf-border-hover)',
                  borderRadius: 'var(--cf-radius-md)',
                  padding: '8px 12px',
                  fontSize: '11px',
                  boxShadow: 'var(--cf-shadow-glass)',
                  pointerEvents: 'none',
                  zIndex: 20,
                  minWidth: '150px',
                }}
              >
                <div style={{ color: 'var(--cf-text-muted)', marginBottom: '4px', fontWeight: 600 }}>
                  {new Date(hBar.timestamp).toLocaleDateString(undefined, {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '3px 8px', color: 'var(--cf-text-secondary)' }}>
                  <span>Open:</span>
                  <span style={{ color: 'var(--cf-text-primary)', textAlign: 'right', fontWeight: 600 }}>
                    ${Number(hBar.open ?? hBar.price).toFixed(2)}
                  </span>
                  <span>High:</span>
                  <span style={{ color: 'var(--cf-bullish)', textAlign: 'right', fontWeight: 600 }}>
                    ${Number(hBar.high ?? hBar.price).toFixed(2)}
                  </span>
                  <span>Low:</span>
                  <span style={{ color: 'var(--cf-bearish)', textAlign: 'right', fontWeight: 600 }}>
                    ${Number(hBar.low ?? hBar.price).toFixed(2)}
                  </span>
                  <span>Close:</span>
                  <span style={{ color: 'var(--cf-text-primary)', textAlign: 'right', fontWeight: 700 }}>
                    ${Number(hBar.close ?? hBar.price).toFixed(2)}
                  </span>
                  {hBar.volume && (
                    <>
                      <span>Volume:</span>
                      <span style={{ color: 'var(--cf-text-primary)', textAlign: 'right', fontWeight: 500 }}>
                        {Number(hBar.volume).toLocaleString()}
                      </span>
                    </>
                  )}
                </div>
              </div>
            )
          })()
        )}
      </div>
    </div>
  )
}
