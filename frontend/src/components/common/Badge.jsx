export function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  id,
}) {
  const variantStyles = {
    bullish: {
      backgroundColor: 'var(--cf-bullish-bg)',
      color: 'var(--cf-bullish)',
      borderColor: 'var(--cf-bullish-border)',
    },
    bearish: {
      backgroundColor: 'var(--cf-bearish-bg)',
      color: 'var(--cf-bearish)',
      borderColor: 'var(--cf-bearish-border)',
    },
    brand: {
      backgroundColor: 'rgba(59, 130, 246, 0.14)',
      color: 'var(--cf-brand-primary)',
      borderColor: 'rgba(59, 130, 246, 0.3)',
    },
    warning: {
      backgroundColor: 'var(--cf-warning-bg)',
      color: 'var(--cf-warning)',
      borderColor: 'rgba(245, 158, 11, 0.3)',
    },
    neutral: {
      backgroundColor: 'rgba(255, 255, 255, 0.06)',
      color: 'var(--cf-text-secondary)',
      borderColor: 'var(--cf-border)',
    },
  }

  const sizeStyles = {
    sm: { padding: '2px 8px', fontSize: '11px', fontWeight: '500' },
    md: { padding: '4px 10px', fontSize: '12px', fontWeight: '600' },
    lg: { padding: '6px 14px', fontSize: '13px', fontWeight: '600' },
  }

  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    borderRadius: 'var(--cf-radius-full)',
    border: '1px solid',
    lineHeight: 1,
    letterSpacing: '0.02em',
    ...variantStyles[variant] || variantStyles.neutral,
    ...sizeStyles[size] || sizeStyles.md,
  }

  return (
    <span id={id} style={baseStyle}>
      {children}
    </span>
  )
}
