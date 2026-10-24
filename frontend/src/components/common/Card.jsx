export function Card({
  children,
  title,
  subtitle,
  action,
  id,
  className = '',
  style = {},
  hoverable = false,
}) {
  const cardStyle = {
    background: 'var(--cf-bg-surface-glass)',
    backdropFilter: 'blur(12px)',
    border: '1px solid var(--cf-border)',
    borderRadius: 'var(--cf-radius-lg)',
    padding: 'var(--cf-space-5)',
    boxShadow: 'var(--cf-shadow-md)',
    transition: 'transform var(--cf-transition-normal), border-color var(--cf-transition-normal), box-shadow var(--cf-transition-normal)',
    ...(hoverable ? { cursor: 'pointer' } : {}),
    ...style,
  }

  return (
    <article
      id={id}
      className={`cf-card ${hoverable ? 'cf-card-hoverable' : ''} ${className}`}
      style={cardStyle}
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
          }}
        >
          <div>
            {title && (
              <h3
                style={{
                  fontSize: '16px',
                  margin: 0,
                  color: 'var(--cf-text-primary)',
                  fontWeight: 600,
                }}
              >
                {title}
              </h3>
            )}
            {subtitle && (
              <p
                style={{
                  fontSize: '12px',
                  margin: '4px 0 0 0',
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
