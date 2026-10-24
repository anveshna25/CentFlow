export function ErrorBanner({
  error,
  onRetry,
  id = 'cf-error-banner',
}) {
  const message = typeof error === 'string' ? error : error?.message || 'An error occurred.'
  const code = error?.code || 'ERROR'

  return (
    <div
      id={id}
      role="alert"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--cf-space-4) var(--cf-space-5)',
        background: 'var(--cf-bearish-bg)',
        border: '1px solid var(--cf-bearish-border)',
        borderRadius: 'var(--cf-radius-md)',
        color: 'var(--cf-bearish)',
        marginBottom: 'var(--cf-space-4)',
        gap: 'var(--cf-space-4)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-3)' }}>
        <span style={{ fontSize: '18px', lineHeight: 1 }}>⚠</span>
        <div>
          <span style={{ fontWeight: 600, fontSize: '13px', display: 'block' }}>
            [{code}] {message}
          </span>
        </div>
      </div>
      {onRetry && (
        <button
          id={`${id}-retry-button`}
          onClick={onRetry}
          style={{
            background: 'rgba(239, 68, 68, 0.2)',
            color: 'var(--cf-bearish)',
            border: '1px solid var(--cf-bearish-border)',
            borderRadius: 'var(--cf-radius-sm)',
            padding: '4px 12px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'background var(--cf-transition-fast)',
          }}
        >
          Retry
        </button>
      )}
    </div>
  )
}
