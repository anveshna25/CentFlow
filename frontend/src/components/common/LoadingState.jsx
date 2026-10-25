
/**
 * Reusable LoadingState component for CentFlow views, cards, and data panels.
 * Provides consistent, layout-stable loading states with animated spinners and contextual messaging.
 */
export function LoadingState({
  title = 'Loading data...',
  description = null,
  size = 'md', // 'sm' | 'md' | 'lg'
  minHeight = '200px',
  inline = false,
  id = 'cf-loading-state',
}) {
  const spinnerSizes = {
    sm: { diameter: '24px', borderWidth: '2.5px' },
    md: { diameter: '36px', borderWidth: '3px' },
    lg: { diameter: '48px', borderWidth: '4px' },
  }

  const { diameter, borderWidth } = spinnerSizes[size] || spinnerSizes.md

  if (inline) {
    return (
      <div
        id={id}
        role="status"
        aria-live="polite"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 'var(--cf-space-3)',
          padding: 'var(--cf-space-2) var(--cf-space-3)',
          color: 'var(--cf-text-secondary)',
          fontSize: size === 'sm' ? '12px' : '13px',
        }}
      >
        <div
          style={{
            width: diameter,
            height: diameter,
            border: `${borderWidth} solid rgba(59, 130, 246, 0.15)`,
            borderTop: `${borderWidth} solid var(--cf-brand-primary)`,
            borderRadius: '50%',
            animation: 'cf-spin 0.8s linear infinite',
            flexShrink: 0,
          }}
        />
        <span>{title}</span>
        <style>{`
          @keyframes cf-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div
      id={id}
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight,
        width: '100%',
        padding: 'var(--cf-space-6)',
        textAlign: 'center',
        background: 'var(--cf-bg-surface-subtle)',
        borderRadius: 'var(--cf-radius-lg)',
        border: '1px solid var(--cf-border)',
      }}
    >
      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 'var(--cf-space-4)',
        }}
      >
        {/* Subtle glow circle behind spinner */}
        <div
          style={{
            position: 'absolute',
            width: `calc(${diameter} + 24px)`,
            height: `calc(${diameter} + 24px)`,
            borderRadius: '50%',
            background: 'var(--cf-brand-glow)',
            filter: 'blur(12px)',
            opacity: 0.6,
          }}
        />
        <div
          style={{
            width: diameter,
            height: diameter,
            border: `${borderWidth} solid rgba(59, 130, 246, 0.18)`,
            borderTop: `${borderWidth} solid var(--cf-brand-primary)`,
            borderRight: `${borderWidth} solid var(--cf-brand-cyan)`,
            borderRadius: '50%',
            animation: 'cf-spin 0.85s cubic-bezier(0.4, 0, 0.2, 1) infinite',
            position: 'relative',
          }}
        />
      </div>

      <div style={{ maxWidth: '420px' }}>
        <h4
          style={{
            margin: 0,
            fontSize: size === 'sm' ? '13px' : size === 'lg' ? '16px' : '14px',
            fontWeight: 600,
            color: 'var(--cf-text-primary)',
            letterSpacing: '-0.01em',
          }}
        >
          {title}
        </h4>
        {description && (
          <p
            style={{
              margin: '6px 0 0',
              fontSize: '12px',
              color: 'var(--cf-text-secondary)',
              lineHeight: 1.5,
            }}
          >
            {description}
          </p>
        )}
      </div>

      <style>{`
        @keyframes cf-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
