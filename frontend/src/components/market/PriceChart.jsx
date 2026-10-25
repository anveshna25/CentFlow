import { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import { EmptyState } from '../common/EmptyState'

/**
 * Interactive PriceChart component supporting Line and Candlestick modes,
 * customizable timeframes, volume histogram, hover crosshair with synchronized
 * tooltips, technical indicator overlays (SMA 20/50, EMA 12, Bollinger Bands),
 * and oscillator sub-chart panels (RSI 14, MACD 12/26/9).
 */
export function PriceChart({
  data = [],
  indicators = null,
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

  // Indicator toggle state
  const [showSma20, setShowSma20] = useState(false)
  const [showSma50, setShowSma50] = useState(false)
  const [showEma12, setShowEma12] = useState(false)
  const [showBollinger, setShowBollinger] = useState(false)
  const [showRsi, setShowRsi] = useState(false)
  const [showMacd, setShowMacd] = useState(false)

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
  const padding = { top: 24, right: 65, bottom: 20, left: 16 }
  const plotWidth = Math.max(100, containerWidth - padding.left - padding.right)
  const pricePlotHeight = Math.max(80, height * 0.62 - padding.top)
  const volumePlotHeight = Math.max(20, height * 0.16)
  const volumeTop = padding.top + pricePlotHeight + 14

  // Oscillator sub-chart heights
  const rsiHeight = 70
  const macdHeight = 70
  const rsiTop = volumeTop + volumePlotHeight + (showRsi ? 18 : 0)
  const macdTop = rsiTop + (showRsi ? rsiHeight + 18 : 0)
  const totalSvgHeight =
    volumeTop +
    volumePlotHeight +
    (showRsi ? rsiHeight + 24 : 0) +
    (showMacd ? macdHeight + 24 : 0) +
    padding.bottom

  // Process and sort bars chronologically
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

  // RSI coordinate mapper (0 to 100 scale)
  const getRsiY = useCallback(
    (rsiVal) => {
      const r = Math.max(0, Math.min(100, Number(rsiVal)))
      return rsiTop + rsiHeight - (r / 100) * rsiHeight
    },
    [rsiTop, rsiHeight]
  )

  // MACD coordinate mapper
  const { minMacd, maxMacd } = useMemo(() => {
    if (!indicators?.macd) return { minMacd: -1, maxMacd: 1 }
    const m = indicators.macd
    let extreme = 0.5
    const checkVal = (v) => {
      if (v !== null && v !== undefined) {
        const abs = Math.abs(Number(v))
        if (abs > extreme) extreme = abs
      }
    }
    ;(m.macd_line || []).forEach(checkVal)
    ;(m.signal_line || []).forEach(checkVal)
    ;(m.histogram || []).forEach(checkVal)

    return { minMacd: -extreme * 1.15, maxMacd: extreme * 1.15 }
  }, [indicators])

  const getMacdY = useCallback(
    (val) => {
      const v = Number(val)
      const ratio = (v - minMacd) / (maxMacd - minMacd || 1)
      return macdTop + macdHeight - ratio * macdHeight
    },
    [minMacd, maxMacd, macdTop, macdHeight]
  )

  // Helper to construct SVG path from indicator series
  const buildSeriesPath = useCallback(
    (series) => {
      if (!series || series.length === 0 || sortedBars.length === 0) return ''
      let path = ''
      let inSegment = false

      // Match length or align to sortedBars
      const len = Math.min(sortedBars.length, series.length)
      for (let i = 0; i < len; i++) {
        const val = series[i]
        if (val !== null && val !== undefined) {
          const x = getX(i)
          const y = getY(val)
          if (!inSegment) {
            path += `M ${x.toFixed(1)},${y.toFixed(1)} `
            inSegment = true
          } else {
            path += `L ${x.toFixed(1)},${y.toFixed(1)} `
          }
        } else {
          inSegment = false
        }
      }
      return path
    },
    [getX, getY, sortedBars.length]
  )

  // Bollinger Bands paths (Upper, Middle, Lower, and shaded envelope)
  const { bbUpperPath, bbLowerPath, bbMiddlePath, bbAreaPath } = useMemo(() => {
    if (!indicators?.bollinger) return { bbUpperPath: '', bbLowerPath: '', bbMiddlePath: '', bbAreaPath: '' }
    const { upper_band, middle_band, lower_band } = indicators.bollinger
    const uPath = buildSeriesPath(upper_band)
    const mPath = buildSeriesPath(middle_band)
    const lPath = buildSeriesPath(lower_band)

    // Build shaded cloud polygon between upper and lower
    let areaP = ''
    if (upper_band && lower_band) {
      const len = Math.min(sortedBars.length, upper_band.length, lower_band.length)
      const upperPoints = []
      const lowerPoints = []
      for (let i = 0; i < len; i++) {
        const u = upper_band[i]
        const l = lower_band[i]
        if (u !== null && u !== undefined && l !== null && l !== undefined) {
          upperPoints.push(`${getX(i).toFixed(1)},${getY(u).toFixed(1)}`)
          lowerPoints.unshift(`${getX(i).toFixed(1)},${getY(l).toFixed(1)}`)
        }
      }
      if (upperPoints.length > 0) {
        areaP = `M ${upperPoints.join(' L ')} L ${lowerPoints.join(' L ')} Z`
      }
    }

    return { bbUpperPath: uPath, bbLowerPath: lPath, bbMiddlePath: mPath, bbAreaPath: areaP }
  }, [indicators, sortedBars.length, buildSeriesPath, getX, getY])

  // RSI Path
  const rsiPath = useMemo(() => {
    if (!indicators?.rsi || !showRsi) return ''
    let path = ''
    let inSeg = false
    const len = Math.min(sortedBars.length, indicators.rsi.length)
    for (let i = 0; i < len; i++) {
      const val = indicators.rsi[i]
      if (val !== null && val !== undefined) {
        const x = getX(i)
        const y = getRsiY(val)
        if (!inSeg) {
          path += `M ${x.toFixed(1)},${y.toFixed(1)} `
          inSeg = true
        } else {
          path += `L ${x.toFixed(1)},${y.toFixed(1)} `
        }
      } else {
        inSeg = false
      }
    }
    return path
  }, [indicators, showRsi, sortedBars.length, getX, getRsiY])

  // MACD Paths
  const { macdLinePath, macdSignalPath } = useMemo(() => {
    if (!indicators?.macd || !showMacd) return { macdLinePath: '', macdSignalPath: '' }
    const { macd_line, signal_line } = indicators.macd

    const buildMacdPath = (series) => {
      if (!series) return ''
      let path = ''
      let inSeg = false
      const len = Math.min(sortedBars.length, series.length)
      for (let i = 0; i < len; i++) {
        const val = series[i]
        if (val !== null && val !== undefined) {
          const x = getX(i)
          const y = getMacdY(val)
          if (!inSeg) {
            path += `M ${x.toFixed(1)},${y.toFixed(1)} `
            inSeg = true
          } else {
            path += `L ${x.toFixed(1)},${y.toFixed(1)} `
          }
        } else {
          inSeg = false
        }
      }
      return path
    }

    return {
      macdLinePath: buildMacdPath(macd_line),
      macdSignalPath: buildMacdPath(signal_line),
    }
  }, [indicators, showMacd, sortedBars.length, getX, getMacdY])

  // Generate SVG path for primary price line and area gradient
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

  // Interactive mouse move for synchronized crosshair
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

  // Active bar and indicator readings under crosshair
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

      {/* Technical Indicators Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          padding: '4px 0',
          fontSize: '11px',
        }}
      >
        <span style={{ color: 'var(--cf-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Overlays:
        </span>
        <button
          id={`${id}-toggle-sma20`}
          onClick={() => setShowSma20(!showSma20)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showSma20 ? '#f59e0b' : 'var(--cf-border)',
            background: showSma20 ? 'rgba(245, 158, 11, 0.15)' : 'var(--cf-bg-base)',
            color: showSma20 ? '#f59e0b' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          SMA 20
        </button>
        <button
          id={`${id}-toggle-sma50`}
          onClick={() => setShowSma50(!showSma50)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showSma50 ? '#ec4899' : 'var(--cf-border)',
            background: showSma50 ? 'rgba(236, 72, 153, 0.15)' : 'var(--cf-bg-base)',
            color: showSma50 ? '#ec4899' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          SMA 50
        </button>
        <button
          id={`${id}-toggle-ema12`}
          onClick={() => setShowEma12(!showEma12)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showEma12 ? 'var(--cf-brand-cyan)' : 'var(--cf-border)',
            background: showEma12 ? 'rgba(6, 182, 212, 0.15)' : 'var(--cf-bg-base)',
            color: showEma12 ? 'var(--cf-brand-cyan)' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          EMA 12
        </button>
        <button
          id={`${id}-toggle-bollinger`}
          onClick={() => setShowBollinger(!showBollinger)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showBollinger ? '#818cf8' : 'var(--cf-border)',
            background: showBollinger ? 'rgba(129, 140, 248, 0.15)' : 'var(--cf-bg-base)',
            color: showBollinger ? '#818cf8' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          Bollinger Bands
        </button>

        <span style={{ color: 'var(--cf-border)', margin: '0 4px' }}>|</span>

        <span style={{ color: 'var(--cf-text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Oscillators:
        </span>
        <button
          id={`${id}-toggle-rsi`}
          onClick={() => setShowRsi(!showRsi)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showRsi ? '#c084fc' : 'var(--cf-border)',
            background: showRsi ? 'rgba(192, 132, 252, 0.15)' : 'var(--cf-bg-base)',
            color: showRsi ? '#c084fc' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          RSI (14)
        </button>
        <button
          id={`${id}-toggle-macd`}
          onClick={() => setShowMacd(!showMacd)}
          style={{
            padding: '3px 8px',
            borderRadius: 'var(--cf-radius-sm)',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            border: '1px solid',
            borderColor: showMacd ? '#38bdf8' : 'var(--cf-border)',
            background: showMacd ? 'rgba(56, 189, 248, 0.15)' : 'var(--cf-bg-base)',
            color: showMacd ? '#38bdf8' : 'var(--cf-text-secondary)',
            transition: 'all var(--cf-transition-fast)',
          }}
        >
          MACD (12, 26, 9)
        </button>
      </div>

      {/* Main SVG Area */}
      <div style={{ position: 'relative', width: '100%', minHeight: `${totalSvgHeight}px` }}>
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
          <EmptyState
            id={`${id}-empty-state`}
            icon="chart"
            title="No Historical Observations"
            description={`Historical price observations for ${symbol} are not available for this timeframe.`}
            minHeight="300px"
          />
        ) : (
          <svg
            id={`${id}-svg`}
            width="100%"
            height={totalSvgHeight}
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

            {/* Bollinger Bands Shaded Area & Envelope Lines */}
            {showBollinger && bbAreaPath && (
              <path d={bbAreaPath} fill="rgba(129, 140, 248, 0.08)" />
            )}
            {showBollinger && bbUpperPath && (
              <path d={bbUpperPath} fill="none" stroke="#818cf8" strokeWidth="1.2" strokeDasharray="3 3" />
            )}
            {showBollinger && bbMiddlePath && (
              <path d={bbMiddlePath} fill="none" stroke="#a5b4fc" strokeWidth="1.2" />
            )}
            {showBollinger && bbLowerPath && (
              <path d={bbLowerPath} fill="none" stroke="#818cf8" strokeWidth="1.2" strokeDasharray="3 3" />
            )}

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

            {/* SMA 20 Overlay */}
            {showSma20 && indicators?.sma_20 && (
              <path
                d={buildSeriesPath(indicators.sma_20)}
                fill="none"
                stroke="#f59e0b"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* SMA 50 Overlay */}
            {showSma50 && indicators?.sma_50 && (
              <path
                d={buildSeriesPath(indicators.sma_50)}
                fill="none"
                stroke="#ec4899"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* EMA 12 Overlay */}
            {showEma12 && indicators?.ema_12 && (
              <path
                d={buildSeriesPath(indicators.ema_12)}
                fill="none"
                stroke="var(--cf-brand-cyan)"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

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

            {/* Oscillator Sub-Panel: RSI (14) */}
            {showRsi && (
              <g>
                {/* Separator */}
                <line
                  x1={padding.left}
                  y1={rsiTop - 6}
                  x2={padding.left + plotWidth}
                  y2={rsiTop - 6}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeWidth="1"
                />
                {/* RSI Shaded Channel 30-70 */}
                <rect
                  x={padding.left}
                  y={getRsiY(70)}
                  width={plotWidth}
                  height={getRsiY(30) - getRsiY(70)}
                  fill="rgba(192, 132, 252, 0.04)"
                />
                {/* Reference Lines at 70, 50, 30 */}
                <line
                  x1={padding.left}
                  y1={getRsiY(70)}
                  x2={padding.left + plotWidth}
                  y2={getRsiY(70)}
                  stroke="rgba(239, 68, 68, 0.4)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <line
                  x1={padding.left}
                  y1={getRsiY(50)}
                  x2={padding.left + plotWidth}
                  y2={getRsiY(50)}
                  stroke="rgba(255, 255, 255, 0.1)"
                  strokeDasharray="2 2"
                  strokeWidth="1"
                />
                <line
                  x1={padding.left}
                  y1={getRsiY(30)}
                  x2={padding.left + plotWidth}
                  y2={getRsiY(30)}
                  stroke="rgba(16, 185, 129, 0.4)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                {/* Axis Labels */}
                <text x={padding.left + plotWidth + 8} y={rsiTop + 12} fill="#c084fc" fontSize="9" fontWeight="600">
                  RSI
                </text>
                <text x={padding.left + plotWidth + 8} y={getRsiY(70) + 3} fill="rgba(239, 68, 68, 0.8)" fontSize="8">
                  70
                </text>
                <text x={padding.left + plotWidth + 8} y={getRsiY(30) + 3} fill="rgba(16, 185, 129, 0.8)" fontSize="8">
                  30
                </text>
                {/* RSI Curve */}
                {rsiPath && (
                  <path
                    d={rsiPath}
                    fill="none"
                    stroke="#c084fc"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                )}
              </g>
            )}

            {/* Oscillator Sub-Panel: MACD (12, 26, 9) */}
            {showMacd && (
              <g>
                {/* Separator */}
                <line
                  x1={padding.left}
                  y1={macdTop - 6}
                  x2={padding.left + plotWidth}
                  y2={macdTop - 6}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeWidth="1"
                />
                {/* Zero Center Line */}
                <line
                  x1={padding.left}
                  y1={getMacdY(0)}
                  x2={padding.left + plotWidth}
                  y2={getMacdY(0)}
                  stroke="rgba(255, 255, 255, 0.18)"
                  strokeWidth="1"
                />
                {/* MACD Histogram Bars */}
                {indicators?.macd?.histogram &&
                  sortedBars.map((_, idx) => {
                    const hist = indicators.macd.histogram[idx]
                    if (hist === null || hist === undefined) return null
                    const x = getX(idx)
                    const y0 = getMacdY(0)
                    const yVal = getMacdY(hist)
                    const barTop = Math.min(y0, yVal)
                    const barH = Math.max(1, Math.abs(yVal - y0))
                    const barColor = hist >= 0 ? 'rgba(16, 185, 129, 0.65)' : 'rgba(239, 68, 68, 0.65)'
                    const bWidth = Math.max(1, candleWidth * 0.6)
                    return (
                      <rect
                        key={`hist-${idx}`}
                        x={x - bWidth / 2}
                        y={barTop}
                        width={bWidth}
                        height={barH}
                        fill={barColor}
                        rx="1"
                      />
                    )
                  })}
                {/* MACD Line & Signal Line */}
                {macdLinePath && (
                  <path d={macdLinePath} fill="none" stroke="#38bdf8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                )}
                {macdSignalPath && (
                  <path d={macdSignalPath} fill="none" stroke="#fb923c" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                )}
                {/* Axis Labels */}
                <text x={padding.left + plotWidth + 8} y={macdTop + 12} fill="#38bdf8" fontSize="9" fontWeight="600">
                  MACD
                </text>
                <text x={padding.left + plotWidth + 8} y={getMacdY(0) + 3} fill="var(--cf-text-muted)" fontSize="8">
                  0
                </text>
              </g>
            )}

            {/* Synchronized Hover Crosshair */}
            {hoverIndex !== null && sortedBars[hoverIndex] && (
              (() => {
                const hX = getX(hoverIndex)
                const hY = getY(sortedBars[hoverIndex].close ?? sortedBars[hoverIndex].price)
                const fullChartBottom =
                  volumeTop +
                  volumePlotHeight +
                  (showRsi ? rsiHeight + 24 : 0) +
                  (showMacd ? macdHeight + 24 : 0)

                return (
                  <g>
                    {/* Full Vertical Crosshair */}
                    <line
                      x1={hX}
                      y1={padding.top}
                      x2={hX}
                      y2={fullChartBottom}
                      stroke="rgba(255, 255, 255, 0.35)"
                      strokeWidth="1"
                      strokeDasharray="3 3"
                    />
                    {/* Horizontal Price Crosshair */}
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

            // Look up indicator readings for the active hover index
            const hSma20 = indicators?.sma_20 ? indicators.sma_20[hoverIndex] : null
            const hSma50 = indicators?.sma_50 ? indicators.sma_50[hoverIndex] : null
            const hEma12 = indicators?.ema_12 ? indicators.ema_12[hoverIndex] : null
            const hRsi = indicators?.rsi ? indicators.rsi[hoverIndex] : null
            const hBb = indicators?.bollinger
              ? {
                  upper: indicators.bollinger.upper_band[hoverIndex],
                  mid: indicators.bollinger.middle_band[hoverIndex],
                  lower: indicators.bollinger.lower_band[hoverIndex],
                }
              : null
            const hMacd = indicators?.macd
              ? {
                  line: indicators.macd.macd_line[hoverIndex],
                  sig: indicators.macd.signal_line[hoverIndex],
                  hist: indicators.macd.histogram[hoverIndex],
                }
              : null

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
                  minWidth: '160px',
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
                  {showSma20 && hSma20 !== null && (
                    <>
                      <span style={{ color: '#f59e0b' }}>SMA 20:</span>
                      <span style={{ color: '#f59e0b', textAlign: 'right', fontWeight: 600 }}>
                        ${Number(hSma20).toFixed(2)}
                      </span>
                    </>
                  )}
                  {showSma50 && hSma50 !== null && (
                    <>
                      <span style={{ color: '#ec4899' }}>SMA 50:</span>
                      <span style={{ color: '#ec4899', textAlign: 'right', fontWeight: 600 }}>
                        ${Number(hSma50).toFixed(2)}
                      </span>
                    </>
                  )}
                  {showEma12 && hEma12 !== null && (
                    <>
                      <span style={{ color: 'var(--cf-brand-cyan)' }}>EMA 12:</span>
                      <span style={{ color: 'var(--cf-brand-cyan)', textAlign: 'right', fontWeight: 600 }}>
                        ${Number(hEma12).toFixed(2)}
                      </span>
                    </>
                  )}
                  {showBollinger && hBb && hBb.upper !== null && (
                    <>
                      <span style={{ color: '#818cf8' }}>BB Upper:</span>
                      <span style={{ color: '#818cf8', textAlign: 'right', fontWeight: 600 }}>
                        ${Number(hBb.upper).toFixed(2)}
                      </span>
                      <span style={{ color: '#818cf8' }}>BB Lower:</span>
                      <span style={{ color: '#818cf8', textAlign: 'right', fontWeight: 600 }}>
                        ${Number(hBb.lower).toFixed(2)}
                      </span>
                    </>
                  )}
                  {showRsi && hRsi !== null && (
                    <>
                      <span style={{ color: '#c084fc' }}>RSI:</span>
                      <span style={{ color: '#c084fc', textAlign: 'right', fontWeight: 600 }}>
                        {Number(hRsi).toFixed(1)}
                      </span>
                    </>
                  )}
                  {showMacd && hMacd && hMacd.line !== null && (
                    <>
                      <span style={{ color: '#38bdf8' }}>MACD:</span>
                      <span style={{ color: '#38bdf8', textAlign: 'right', fontWeight: 600 }}>
                        {Number(hMacd.line).toFixed(2)}
                      </span>
                      <span style={{ color: '#fb923c' }}>Signal:</span>
                      <span style={{ color: '#fb923c', textAlign: 'right', fontWeight: 600 }}>
                        {Number(hMacd.sig).toFixed(2)}
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
