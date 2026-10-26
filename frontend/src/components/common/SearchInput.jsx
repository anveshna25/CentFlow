import { Input } from './Input'

/**
 * Standardized CentFlow SearchInput Primitive
 * Preconfigured with magnifying glass icon and interactive clear button.
 */
export function SearchInput({
  value = '',
  onChange,
  onClear,
  placeholder = 'Search instruments, symbols, or assets...',
  id = 'cf-search-input',
  size = 'md',
  ...props
}) {
  const hasValue = Boolean(value && String(value).length > 0)

  const handleClear = () => {
    if (onClear) {
      onClear()
    } else if (onChange) {
      onChange({ target: { value: '' } })
    }
  }

  const clearButton = hasValue ? (
    <button
      type="button"
      onClick={handleClear}
      aria-label="Clear search input"
      style={{
        background: 'transparent',
        border: 'none',
        color: 'var(--cf-text-muted)',
        cursor: 'pointer',
        padding: '2px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 'var(--cf-radius-full)',
        fontSize: '12px',
        lineHeight: 1,
        transition: 'color var(--cf-transition-fast)',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--cf-text-primary)')}
      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--cf-text-muted)')}
    >
      ✕
    </button>
  ) : null

  const searchIcon = (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )

  return (
    <Input
      id={id}
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      iconLeft={searchIcon}
      iconRight={clearButton}
      size={size}
      {...props}
    />
  )
}
