/**
 * Standardized CentFlow Skeleton Loader Primitive
 * Provides layout-stable shimmer placeholders during asynchronous data fetches.
 */
export function Skeleton({
  width = '100%',
  height = '20px',
  borderRadius = 'var(--cf-radius-sm)',
  className = '',
  style = {},
}) {
  return (
    <div
      className={`cf-skeleton ${className}`}
      aria-hidden="true"
      style={{
        width,
        height,
        borderRadius,
        background: 'linear-gradient(90deg, var(--cf-bg-surface-elevated) 25%, var(--cf-border) 50%, var(--cf-bg-surface-elevated) 75%)',
        backgroundSize: '200% 100%',
        animation: 'cf-shimmer 1.8s infinite',
        display: 'inline-block',
        ...style,
      }}
    >
      <style>{`
        @keyframes cf-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
      `}</style>
    </div>
  )
}
