import { Badge } from '../common/Badge'

export function Header({ onSearch, searchValue = '' }) {
  return (
    <header
      id="cf-global-header"
      style={{
        height: '64px',
        borderBottom: '1px solid var(--cf-border)',
        background: 'rgba(10, 14, 23, 0.8)',
        backdropFilter: 'blur(16px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--cf-space-6)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-4)' }}>
        <div style={{ position: 'relative', width: '280px' }}>
          <input
            id="cf-search-input"
            type="search"
            placeholder="Search symbols, assets, markets..."
            value={searchValue}
            onChange={(e) => onSearch && onSearch(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--cf-bg-surface-elevated)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-full)',
              padding: '8px 16px',
              color: 'var(--cf-text-primary)',
              fontSize: '13px',
              outline: 'none',
              transition: 'border-color var(--cf-transition-fast), box-shadow var(--cf-transition-fast)',
            }}
          />
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--cf-space-2)' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: 'var(--cf-bullish)',
              boxShadow: '0 0 8px var(--cf-bullish)',
              display: 'inline-block',
            }}
          />
          <span style={{ fontSize: '12px', color: 'var(--cf-text-secondary)', fontWeight: 500 }}>
            Market Data: Connected
          </span>
        </div>

        <Badge variant="brand" size="sm">
          Core Engine v0.1.0
        </Badge>
      </div>
    </header>
  )
}
