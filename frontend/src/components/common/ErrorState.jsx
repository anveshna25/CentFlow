import { Button } from './Button'

/**
 * Maps technical error codes or strings to user-friendly messages.
 * Prevents leaking raw internal stack traces, database syntax, or unhandled errors.
 */
function sanitizeErrorMessage(error) {
  if (!error) return 'An unexpected error occurred while processing market data.'

  const message = typeof error === 'string' ? error : error.message || ''
  const code = error?.code || ''

  // Known API/Network error mappings
  if (code === 'NETWORK_ERROR' || message.includes('Failed to fetch') || message.includes('NetworkError')) {
    return 'Unable to establish a connection to the market data service. Please check your network connection and try again.'
  }
  if (code === 'HTTP_404' || code === 'NOT_FOUND' || message.includes('404')) {
    return 'The requested instrument, quote, or analytical resource could not be found.'
  }
  if (code === 'HTTP_429' || code === 'RATE_LIMITED' || message.includes('429')) {
    return 'Market data request limit reached. Please wait a moment before trying again.'
  }
  if (code === 'HTTP_500' || code === 'INTERNAL_SERVER_ERROR' || message.includes('500')) {
    return 'The market data server encountered a temporary issue. Our data feed will resume shortly.'
  }
  if (code === 'VALIDATION_ERROR' || message.includes('validation')) {
    return 'The request contained invalid parameters. Please verify your search or timeframe selection.'
  }

  // Filter out raw SQL or stack traces if present
  if (message.includes('Traceback') || message.includes('SELECT ') || message.includes('SQLAlchemy')) {
    return 'A server processing error occurred. Please try again or refresh the page.'
  }

  return message || 'An unexpected error occurred. Please try again.'
}

/**
 * Reusable ErrorState component for CentFlow.
 * Presents a sanitized, user-friendly error display with optional retry actions and CentFlow styling.
 */
export function ErrorState({
  error,
  title = 'Unable to Load Market Data',
  message = null,
  onRetry = null,
  retryLabel = 'Try Again',
  secondaryAction = null, // { label, onClick }
  compact = false,
  minHeight = '200px',
  id = 'cf-error-state',
}) {
  const displayMessage = message || sanitizeErrorMessage(error)
  const errorCode = error?.code && error.code !== 'API_ERROR' ? error.code : null

  if (compact) {
    return (
      <div
        id={id}
        role="alert"
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--cf-space-3) var(--cf-space-4)',
          background: 'var(--cf-bearish-bg)',
          border: '1px solid var(--cf-bearish-border)',
          borderRadius: 'var(--cf-radius-md)',
          color: 'var(--cf-bearish)',
          fontSize: '13px',
          gap: 'var(--cf-space-3)',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)', minWidth: 0, flex: 1 }}>
          <span style={{ fontSize: '16px', lineHeight: 1, flexShrink: 0 }}>⚠</span>
          <span style={{ fontWeight: 500, color: 'var(--cf-text-primary)' }}>
            {displayMessage}
          </span>
          {errorCode && (
            <span
              style={{
                fontSize: '11px',
                padding: '1px 6px',
                borderRadius: 'var(--cf-radius-sm)',
                background: 'rgba(239, 68, 68, 0.2)',
                color: 'var(--cf-bearish)',
                fontWeight: 600,
              }}
            >
              {errorCode}
            </span>
          )}
        </div>
        {onRetry && (
          <Button
            id={`${id}-retry-btn`}
            onClick={onRetry}
            variant="danger"
            size="sm"
          >
            {retryLabel}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div
      id={id}
      role="alert"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight,
        width: '100%',
        padding: 'var(--cf-space-8) var(--cf-space-6)',
        textAlign: 'center',
        background: 'rgba(239, 68, 68, 0.04)',
        borderRadius: 'var(--cf-radius-lg)',
        border: '1px solid var(--cf-bearish-border)',
      }}
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          background: 'rgba(239, 68, 68, 0.12)',
          border: '1px solid var(--cf-bearish-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 'var(--cf-space-4)',
          color: 'var(--cf-bearish)',
          fontSize: '22px',
        }}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>

      <h3
        style={{
          margin: 0,
          fontSize: '16px',
          fontWeight: 600,
          color: 'var(--cf-text-primary)',
          letterSpacing: '-0.01em',
        }}
      >
        {title}
      </h3>

      <p
        style={{
          margin: '8px 0 0',
          fontSize: '13px',
          color: 'var(--cf-text-secondary)',
          maxWidth: '460px',
          lineHeight: 1.5,
        }}
      >
        {displayMessage}
      </p>

      {errorCode && (
        <span
          style={{
            marginTop: 'var(--cf-space-2)',
            fontSize: '11px',
            color: 'var(--cf-text-muted)',
            fontFamily: 'monospace',
          }}
        >
          Reference: {errorCode}
        </span>
      )}

      {(onRetry || secondaryAction) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--cf-space-3)',
            marginTop: 'var(--cf-space-5)',
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          {onRetry && (
            <Button
              id={`${id}-retry-btn`}
              onClick={onRetry}
              variant="primary"
              size="md"
            >
              {retryLabel}
            </Button>
          )}
          {secondaryAction && (
            <Button
              id={`${id}-secondary-btn`}
              onClick={secondaryAction.onClick}
              variant="secondary"
              size="md"
            >
              {secondaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
