import { Badge } from '../common/Badge'

export function StatWidget({
  title,
  value,
  changePercent,
  subtitle,
  id,
}) {
  const isPositive = typeof changePercent === 'number' ? changePercent >= 0 : !String(changePercent || '').startsWith('-')
  const variant = isPositive ? 'bullish' : 'bearish'

  return (
    <div
      id={id}
      style={{
        background: 'var(--cf-bg-surface-glass)',
        border: '1px solid var(--cf-border)',
        borderRadius: 'var(--cf-radius-lg)',
        padding: 'var(--cf-space-5)',
        backdropFilter: 'blur(12px)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--cf-space-2)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span
          style={{
            fontSize: '12px',
            color: 'var(--cf-text-secondary)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
          }}
        >
          {title}
        </span>
        {changePercent !== undefined && (
          <Badge variant={variant} size="sm">
            {isPositive ? '▲ +' : '▼ '}
            {typeof changePercent === 'number' ? `${changePercent.toFixed(2)}%` : changePercent}
          </Badge>
        )}
      </div>

      <div
        style={{
          fontSize: '26px',
          fontFamily: 'var(--cf-font-display)',
          fontWeight: 700,
          color: 'var(--cf-text-primary)',
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>

      {subtitle && (
        <span
          style={{
            fontSize: '12px',
            color: 'var(--cf-text-muted)',
          }}
        >
          {subtitle}
        </span>
      )}
    </div>
  )
}
