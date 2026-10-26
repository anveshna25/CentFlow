import { Button } from './Button'

/**
 * Standardized CentFlow StaleDataBanner Primitive
 * Displays a non-intrusive indicator when financial data is delayed, cached, or exceeds freshness thresholds.
 */
export function StaleDataBanner({
  timestamp,
  message = 'Market data may be delayed or stale.',
  onRefresh,
  isRefreshing = false,
  id = 'cf-stale-banner',
  className = '',
  style = {},
}) {
  const formattedTime = timestamp
    ? new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null

  return (
    <aside
      id={id}
      role="status"
      className={`cf-stale-banner ${className}`}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 'var(--cf-space-3)',
        padding: 'var(--cf-space-3) var(--cf-space-4)',
        background: 'var(--cf-warning-bg)',
        border: '1px solid var(--cf-warning-border)',
        borderRadius: 'var(--cf-radius-md)',
        color: 'var(--cf-warning)',
        fontSize: 'var(--cf-font-size-sm)',
        boxSizing: 'border-box',
        ...style,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)' }}>
        <span aria-hidden="true" style={{ fontSize: '15px' }}>
          ⚠️
        </span>
        <span>
          <strong>Notice:</strong> {message}
          {formattedTime && (
            <span style={{ opacity: 0.85, marginLeft: '6px' }}>
              (Last synced: {formattedTime})
            </span>
          )}
        </span>
      </div>

      {onRefresh && (
        <Button
          variant="secondary"
          size="sm"
          isLoading={isRefreshing}
          onClick={onRefresh}
          style={{
            borderColor: 'var(--cf-warning-border)',
            color: 'var(--cf-text-primary)',
          }}
        >
          Refresh Data
        </Button>
      )}
    </aside>
  )
}
