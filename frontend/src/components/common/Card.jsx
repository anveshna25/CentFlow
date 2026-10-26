/**
 * Standardized CentFlow Card Container Primitive
 * Provides consistent glassmorphism surface, border, padding,
 * header hierarchy, and optional hover elevation.
 */
export function Card({
  children,
  title,
  subtitle,
  action = null,
  id,
  className = '',
  style = {},
  hoverable = false,
  onClick,
}) {
  const cardStyle = {
    background: 'var(--cf-bg-surface-glass)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    border: '1px solid var(--cf-border)',
    borderRadius: 'var(--cf-radius-lg)',
    padding: 'var(--cf-space-5)',
    boxShadow: 'var(--cf-shadow-sm)',
    transition:
      'transform var(--cf-transition-normal), border-color var(--cf-transition-normal), box-shadow var(--cf-transition-normal)',
    ...(hoverable || onClick ? { cursor: 'pointer' } : {}),
    ...style,
  }

  return (
    <article
      id={id}
      onClick={onClick}
      className={`cf-card ${hoverable || onClick ? 'cf-card-hoverable' : ''} ${className}`}
      style={cardStyle}
      onMouseEnter={
        hoverable || onClick
          ? (e) => {
              e.currentTarget.style.borderColor = 'var(--cf-border-hover)'
              e.currentTarget.style.boxShadow = 'var(--cf-shadow-md)'
            }
          : undefined
      }
      onMouseLeave={
        hoverable || onClick
          ? (e) => {
              e.currentTarget.style.borderColor = 'var(--cf-border)'
              e.currentTarget.style.boxShadow = 'var(--cf-shadow-sm)'
            }
          : undefined
      }
    >
      {(title || subtitle || action) && (
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 'var(--cf-space-4)',
            borderBottom: subtitle || title ? '1px solid var(--cf-border)' : 'none',
            paddingBottom: subtitle || title ? 'var(--cf-space-3)' : '0',
            gap: 'var(--cf-space-3)',
          }}
        >
          <div>
            {title && (
              <h3
                style={{
                  fontSize: 'var(--cf-font-size-lg)',
                  margin: 0,
                  color: 'var(--cf-text-primary)',
                  fontWeight: 'var(--cf-font-weight-semibold)',
                  letterSpacing: '-0.01em',
                }}
              >
                {title}
              </h3>
            )}
            {subtitle && (
              <p
                style={{
                  fontSize: 'var(--cf-font-size-sm)',
                  margin: 'var(--cf-space-1) 0 0 0',
                  color: 'var(--cf-text-secondary)',
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </header>
      )}
      <div>{children}</div>
    </article>
  )
}
