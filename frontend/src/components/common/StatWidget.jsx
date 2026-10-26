import { Badge } from './Badge'

/**
 * Standardized CentFlow StatWidget / MetricCard Primitive
 * Displays headline metric values with tabular alignment, change percentage badge,
 * trend indication, subtitle context, and optional sparkline/action slots.
 */
export function StatWidget({
  title,
  value,
  changePercent,
  subtitle,
  extra = null,
  sparkline = null,
  status = null, // 'live' | 'delayed' | 'stale' | null
  id,
  className = '',
  style = {},
  onClick,
}) {
  const isPositive =
    typeof changePercent === 'number'
      ? changePercent >= 0
      : !String(changePercent || '').startsWith('-')

  const variant = isPositive ? 'bullish' : 'bearish'

  const statusColors = {
    live: 'var(--cf-bullish)',
    delayed: 'var(--cf-warning)',
    stale: 'var(--cf-text-muted)',
  }

  return (
    <article
      id={id}
      onClick={onClick}
      className={`cf-stat-widget ${onClick ? 'cf-stat-widget-clickable' : ''} ${className}`}
      style={{
        background: 'var(--cf-bg-surface-glass)',
        border: '1px solid var(--cf-border)',
        borderRadius: 'var(--cf-radius-lg)',
        padding: 'var(--cf-space-5)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--cf-space-2)',
        position: 'relative',
        overflow: 'hidden',
        cursor: onClick ? 'pointer' : 'default',
        boxShadow: 'var(--cf-shadow-sm)',
        transition:
          'border-color var(--cf-transition-fast), transform var(--cf-transition-fast), box-shadow var(--cf-transition-fast)',
        ...style,
      }}
      onMouseEnter={
        onClick
          ? (e) => {
              e.currentTarget.style.borderColor = 'var(--cf-brand-primary)'
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = 'var(--cf-shadow-md)'
            }
          : undefined
      }
      onMouseLeave={
        onClick
          ? (e) => {
              e.currentTarget.style.borderColor = 'var(--cf-border)'
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'var(--cf-shadow-sm)'
            }
          : undefined
      }
    >
      {/* Top Header Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 'var(--cf-space-2)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)' }}>
          {status && (
            <span
              title={`Status: ${status}`}
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                background: statusColors[status] || statusColors.stale,
                boxShadow: status === 'live' ? '0 0 8px var(--cf-bullish)' : 'none',
                flexShrink: 0,
              }}
            />
          )}
          <span
            style={{
              fontSize: 'var(--cf-font-size-xs)',
              color: 'var(--cf-text-secondary)',
              fontWeight: 'var(--cf-font-weight-bold)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
            }}
          >
            {title}
          </span>
        </div>

        {changePercent !== undefined && changePercent !== null && (
          <Badge variant={variant} size="sm">
            {isPositive ? '▲ +' : '▼ '}
            {typeof changePercent === 'number'
              ? `${changePercent.toFixed(2)}%`
              : changePercent}
          </Badge>
        )}
      </div>

      {/* Main Metric Value */}
      <div
        className="cf-num-tabular"
        style={{
          fontSize: 'var(--cf-font-size-3xl)',
          fontFamily: 'var(--cf-font-display)',
          fontWeight: 'var(--cf-font-weight-extrabold)',
          color: 'var(--cf-text-primary)',
          letterSpacing: '-0.02em',
          lineHeight: 1.15,
        }}
      >
        {value}
      </div>

      {/* Optional Sparkline Slot */}
      {sparkline && <div style={{ marginTop: 'var(--cf-space-1)' }}>{sparkline}</div>}

      {/* Footer / Subtitle Context */}
      {subtitle && (
        <span
          style={{
            fontSize: 'var(--cf-font-size-sm)',
            color: 'var(--cf-text-muted)',
            marginTop: 'var(--cf-space-1)',
          }}
        >
          {subtitle}
        </span>
      )}

      {extra && (
        <div
          style={{
            marginTop: 'var(--cf-space-2)',
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--cf-space-2)',
          }}
        >
          {extra}
        </div>
      )}
    </article>
  )
}
