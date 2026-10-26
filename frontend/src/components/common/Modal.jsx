import { useEffect } from 'react'

/**
 * Standardized CentFlow Accessible Modal Dialog Primitive
 * Provides backdrop overlay, escape key handling, body scroll locking,
 * size options (sm, md, lg, xl), header typography, close button, and footer action slots.
 */
export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  headerRight = null,
  footer = null,
  children,
  size = 'md', // 'sm' | 'md' | 'lg' | 'xl'
  closeOnOverlayClick = true,
  closeOnEsc = true,
  id = 'cf-modal',
  contentId,
  className = '',
  style = {},
}) {
  useEffect(() => {
    if (!isOpen) return

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleKeyDown = (e) => {
      if (closeOnEsc && e.key === 'Escape') {
        if (onClose) onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, closeOnEsc, onClose])

  if (!isOpen) return null

  const sizeWidths = {
    sm: '420px',
    md: '580px',
    lg: '780px',
    xl: '960px',
  }

  const maxWidth = sizeWidths[size] || sizeWidths.md

  return (
    <div
      id={id}
      role="presentation"
      onClick={closeOnOverlayClick ? onClose : undefined}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0, 0, 0, 0.76)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--cf-space-4)',
        boxSizing: 'border-box',
        animation: 'cf-fade-in 0.15s ease-out',
      }}
    >
      <div
        id={contentId}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? 'cf-modal-title' : undefined}
        onClick={(e) => e.stopPropagation()}
        className={`cf-modal-content ${className}`}
        style={{
          background: 'var(--cf-bg-surface)',
          border: '1px solid var(--cf-border)',
          borderRadius: 'var(--cf-radius-xl)',
          width: '100%',
          maxWidth,
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--cf-shadow-glass)',
          overflow: 'hidden',
          boxSizing: 'border-box',
          ...style,
        }}
      >
        {/* Modal Header */}
        {(title || subtitle || onClose) && (
          <header
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              padding: 'var(--cf-space-5) var(--cf-space-6)',
              borderBottom: '1px solid var(--cf-border)',
              background: 'var(--cf-bg-surface-elevated)',
              gap: 'var(--cf-space-4)',
              flexShrink: 0,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              {title && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-3)', flexWrap: 'wrap' }}>
                  <h2
                    id="cf-modal-title"
                    style={{
                      fontSize: 'var(--cf-font-size-xl)',
                      fontWeight: 'var(--cf-font-weight-bold)',
                      color: 'var(--cf-text-primary)',
                      margin: 0,
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {title}
                  </h2>
                  {headerRight}
                </div>
              )}
              {subtitle && (
                <p
                  style={{
                    fontSize: 'var(--cf-font-size-sm)',
                    color: 'var(--cf-text-secondary)',
                    margin: 'var(--cf-space-1) 0 0 0',
                  }}
                >
                  {subtitle}
                </p>
              )}
            </div>

            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                style={{
                  background: 'var(--cf-bg-surface)',
                  border: '1px solid var(--cf-border)',
                  color: 'var(--cf-text-secondary)',
                  borderRadius: 'var(--cf-radius-full)',
                  width: '32px',
                  height: '32px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  fontSize: '14px',
                  flexShrink: 0,
                  transition: 'all var(--cf-transition-fast)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'var(--cf-border-hover)'
                  e.currentTarget.style.color = 'var(--cf-text-primary)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'var(--cf-border)'
                  e.currentTarget.style.color = 'var(--cf-text-secondary)'
                }}
              >
                ✕
              </button>
            )}
          </header>
        )}

        {/* Modal Body */}
        <div
          style={{
            padding: 'var(--cf-space-6)',
            overflowY: 'auto',
            flex: 1,
            color: 'var(--cf-text-primary)',
          }}
        >
          {children}
        </div>

        {/* Modal Footer */}
        {footer && (
          <footer
            style={{
              padding: 'var(--cf-space-4) var(--cf-space-6)',
              borderTop: '1px solid var(--cf-border)',
              background: 'var(--cf-bg-surface-elevated)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: 'var(--cf-space-3)',
              flexShrink: 0,
            }}
          >
            {footer}
          </footer>
        )}
      </div>

      <style>{`
        @keyframes cf-fade-in {
          from { opacity: 0; transform: scale(0.98); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}
