/**
 * Standardized CentFlow Button Primitive
 * Supports variants (primary, secondary, ghost, danger, bullish),
 * sizes (sm, md, lg), loading spinner states, and icon slots.
 */
export function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'ghost' | 'danger' | 'bullish'
  size = 'md', // 'sm' | 'md' | 'lg'
  isLoading = false,
  disabled = false,
  iconLeft = null,
  iconRight = null,
  fullWidth = false,
  onClick,
  type = 'button',
  id,
  className = '',
  style = {},
  ...props
}) {
  const sizeStyles = {
    sm: {
      padding: 'var(--cf-space-1) var(--cf-space-3)',
      fontSize: 'var(--cf-font-size-sm)',
      height: '30px',
      gap: 'var(--cf-space-1)',
      borderRadius: 'var(--cf-radius-sm)',
    },
    md: {
      padding: 'var(--cf-space-2) var(--cf-space-4)',
      fontSize: 'var(--cf-font-size-base)',
      height: '38px',
      gap: 'var(--cf-space-2)',
      borderRadius: 'var(--cf-radius-md)',
    },
    lg: {
      padding: 'var(--cf-space-3) var(--cf-space-6)',
      fontSize: 'var(--cf-font-size-md)',
      height: '46px',
      gap: 'var(--cf-space-2)',
      borderRadius: 'var(--cf-radius-lg)',
    },
  }

  const variantStyles = {
    primary: {
      background: 'var(--cf-brand-primary)',
      color: '#ffffff',
      border: '1px solid var(--cf-brand-primary)',
      boxShadow: 'var(--cf-shadow-sm)',
    },
    secondary: {
      background: 'var(--cf-bg-surface-elevated)',
      color: 'var(--cf-text-primary)',
      border: '1px solid var(--cf-border)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--cf-text-secondary)',
      border: '1px solid transparent',
    },
    danger: {
      background: 'var(--cf-bearish-bg)',
      color: 'var(--cf-bearish)',
      border: '1px solid var(--cf-bearish-border)',
    },
    bullish: {
      background: 'var(--cf-bullish-bg)',
      color: 'var(--cf-bullish)',
      border: '1px solid var(--cf-bullish-border)',
    },
  }

  const currentSize = sizeStyles[size] || sizeStyles.md
  const currentVariant = variantStyles[variant] || variantStyles.primary

  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--cf-font-sans)',
    fontWeight: 'var(--cf-font-weight-semibold)',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all var(--cf-transition-fast)',
    width: fullWidth ? '100%' : 'auto',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    boxSizing: 'border-box',
    textDecoration: 'none',
    ...currentSize,
    ...currentVariant,
    ...style,
  }

  return (
    <button
      id={id}
      type={type}
      disabled={disabled || isLoading}
      onClick={disabled || isLoading ? undefined : onClick}
      className={`cf-btn cf-btn-${variant} cf-btn-${size} ${className}`}
      style={baseStyle}
      {...props}
    >
      {isLoading ? (
        <span
          style={{
            width: size === 'sm' ? '12px' : '15px',
            height: size === 'sm' ? '12px' : '15px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'cf-spin 0.6s linear infinite',
            flexShrink: 0,
          }}
        />
      ) : (
        iconLeft
      )}
      <span>{children}</span>
      {!isLoading && iconRight}
    </button>
  )
}
