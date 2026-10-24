export function LoadingSpinner({ message = 'Loading market data...', id = 'cf-loading-spinner' }) {
  return (
    <div
      id={id}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--cf-space-8)',
        gap: 'var(--cf-space-3)',
      }}
    >
      <div
        style={{
          width: '36px',
          height: '36px',
          border: '3px solid rgba(59, 130, 246, 0.15)',
          borderTop: '3px solid var(--cf-brand-primary)',
          borderRadius: '50%',
          animation: 'cf-spin 0.8s linear infinite',
        }}
      />
      {message && (
        <span
          style={{
            fontSize: '13px',
            color: 'var(--cf-text-secondary)',
            fontWeight: 500,
          }}
        >
          {message}
        </span>
      )}
      <style>{`
        @keyframes cf-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
