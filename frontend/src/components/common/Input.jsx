import { useState } from 'react'

/**
 * Standardized CentFlow Input Primitive
 * Provides consistent height, label, helper text, error state, and CentFlow green focus ring.
 */
export function Input({
  label,
  error,
  helperText,
  iconLeft = null,
  iconRight = null,
  size = 'md', // 'sm' | 'md'
  fullWidth = true,
  disabled = false,
  id,
  type = 'text',
  className = '',
  style = {},
  inputStyle = {},
  onFocus,
  onBlur,
  ...props
}) {
  const [isFocused, setIsFocused] = useState(false)

  const sizeStyles = {
    sm: {
      height: '32px',
      fontSize: 'var(--cf-font-size-sm)',
      padding: iconLeft ? '0 var(--cf-space-3) 0 var(--cf-space-7)' : '0 var(--cf-space-3)',
    },
    md: {
      height: '38px',
      fontSize: 'var(--cf-font-size-base)',
      padding: iconLeft ? '0 var(--cf-space-3) 0 var(--cf-space-8)' : '0 var(--cf-space-3)',
    },
  }

  const currentSize = sizeStyles[size] || sizeStyles.md

  const handleFocus = (e) => {
    setIsFocused(true)
    if (onFocus) onFocus(e)
  }

  const handleBlur = (e) => {
    setIsFocused(false)
    if (onBlur) onBlur(e)
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--cf-space-1)',
        width: fullWidth ? '100%' : 'auto',
        ...style,
      }}
      className={`cf-input-container ${className}`}
    >
      {label && (
        <label
          htmlFor={id}
          style={{
            fontSize: 'var(--cf-font-size-sm)',
            fontWeight: 'var(--cf-font-weight-medium)',
            color: error ? 'var(--cf-bearish)' : 'var(--cf-text-secondary)',
          }}
        >
          {label}
        </label>
      )}

      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          width: '100%',
        }}
      >
        {iconLeft && (
          <span
            style={{
              position: 'absolute',
              left: 'var(--cf-space-3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: isFocused ? 'var(--cf-brand-primary)' : 'var(--cf-text-muted)',
              pointerEvents: 'none',
              transition: 'color var(--cf-transition-fast)',
            }}
          >
            {iconLeft}
          </span>
        )}

        <input
          id={id}
          type={type}
          disabled={disabled}
          onFocus={handleFocus}
          onBlur={handleBlur}
          style={{
            width: '100%',
            background: 'var(--cf-bg-surface-elevated)',
            color: 'var(--cf-text-primary)',
            border: `1px solid ${
              error
                ? 'var(--cf-bearish)'
                : isFocused
                ? 'var(--cf-brand-primary)'
                : 'var(--cf-border)'
            }`,
            borderRadius: 'var(--cf-radius-md)',
            outline: 'none',
            boxShadow: isFocused
              ? `0 0 0 2px ${error ? 'var(--cf-bearish-border)' : 'var(--cf-brand-glow)'}`
              : 'none',
            boxSizing: 'border-box',
            fontFamily: 'var(--cf-font-sans)',
            transition: 'border-color var(--cf-transition-fast), box-shadow var(--cf-transition-fast)',
            cursor: disabled ? 'not-allowed' : 'text',
            opacity: disabled ? 0.6 : 1,
            ...currentSize,
            ...(iconRight ? { paddingRight: 'var(--cf-space-8)' } : {}),
            ...inputStyle,
          }}
          {...props}
        />

        {iconRight && (
          <span
            style={{
              position: 'absolute',
              right: 'var(--cf-space-3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--cf-text-muted)',
            }}
          >
            {iconRight}
          </span>
        )}
      </div>

      {(error || helperText) && (
        <span
          style={{
            fontSize: 'var(--cf-font-size-xs)',
            color: error ? 'var(--cf-bearish)' : 'var(--cf-text-muted)',
            marginTop: '2px',
          }}
        >
          {error || helperText}
        </span>
      )}
    </div>
  )
}
