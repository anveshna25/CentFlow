import { Button } from './Button'

/**
 * Default SVG icon presets for financial and workflow empty states.
 */
function EmptyIcon({ type = 'folder', size = 32 }) {
  const strokeProps = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: '1.8',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
  }

  switch (type) {
    case 'search':
      return (
        <svg {...strokeProps}>
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      )
    case 'chart':
      return (
        <svg {...strokeProps}>
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
          <line x1="2" y1="20" x2="22" y2="20" />
        </svg>
      )
    case 'filter':
      return (
        <svg {...strokeProps}>
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        </svg>
      )
    case 'watchlist':
    case 'folder':
    default:
      return (
        <svg {...strokeProps}>
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
          <line x1="12" y1="11" x2="12" y2="17" />
          <line x1="9" y1="14" x2="15" y2="14" />
        </svg>
      )
  }
}

/**
 * Reusable EmptyState component for CentFlow.
 * Clearly communicates absence of data (distinct from system errors) and offers
 * contextual next-step action paths (such as asset search or filter reset).
 */
export function EmptyState({
  title = 'No Data Available',
  description = 'There are currently no records or entries to display in this view.',
  icon = 'folder', // 'folder' | 'search' | 'chart' | 'filter' | custom ReactNode
  action = null, // { label, onClick, id }
  secondaryAction = null, // { label, onClick, id }
  minHeight = '240px',
  compact = false,
  id = 'cf-empty-state',
}) {
  const isPresetIcon = typeof icon === 'string'

  if (compact) {
    return (
      <div
        id={id}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: 'var(--cf-space-4) var(--cf-space-5)',
          background: 'var(--cf-bg-surface-subtle)',
          border: '1px dashed var(--cf-border)',
          borderRadius: 'var(--cf-radius-md)',
          color: 'var(--cf-text-secondary)',
          fontSize: '13px',
          gap: 'var(--cf-space-4)',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-3)' }}>
          <div style={{ color: 'var(--cf-text-muted)', display: 'flex' }}>
            {isPresetIcon ? <EmptyIcon type={icon} size={20} /> : icon}
          </div>
          <div>
            <div style={{ fontWeight: 600, color: 'var(--cf-text-primary)' }}>{title}</div>
            {description && <div style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>{description}</div>}
          </div>
        </div>
        {action && (
          <Button
            id={action.id || `${id}-action-btn`}
            onClick={action.onClick}
            variant="secondary"
            size="sm"
          >
            {action.label}
          </Button>
        )}
      </div>
    )
  }

  return (
    <div
      id={id}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight,
        width: '100%',
        padding: 'var(--cf-space-8) var(--cf-space-6)',
        textAlign: 'center',
        background: 'var(--cf-bg-surface-subtle)',
        borderRadius: 'var(--cf-radius-lg)',
        border: '1px dashed var(--cf-border)',
      }}
    >
      <div
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'var(--cf-bg-surface-elevated)',
          border: '1px solid var(--cf-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 'var(--cf-space-4)',
          color: 'var(--cf-brand-primary)',
          boxShadow: 'var(--cf-shadow-sm)',
        }}
      >
        {isPresetIcon ? <EmptyIcon type={icon} size={26} /> : icon}
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

      {description && (
        <p
          style={{
            margin: '8px 0 0',
            fontSize: '13px',
            color: 'var(--cf-text-secondary)',
            maxWidth: '440px',
            lineHeight: 1.5,
          }}
        >
          {description}
        </p>
      )}

      {(action || secondaryAction) && (
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
          {action && (
            <Button
              id={action.id || `${id}-action-btn`}
              onClick={action.onClick}
              variant="primary"
              size="md"
            >
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <Button
              id={secondaryAction.id || `${id}-secondary-btn`}
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
