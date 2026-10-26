/**
 * Standardized CentFlow Financial Table Primitives
 * Provides clean header hierarchy, subtle borders, row hover transitions,
 * and tabular numeric alignments for high-density financial data.
 */

export function Table({
  children,
  id,
  className = '',
  style = {},
  fullWidth = true,
}) {
  return (
    <div
      style={{
        width: fullWidth ? '100%' : 'auto',
        overflowX: 'auto',
        borderRadius: 'var(--cf-radius-lg)',
        border: '1px solid var(--cf-border)',
        background: 'var(--cf-bg-surface)',
        boxShadow: 'var(--cf-shadow-sm)',
        ...style,
      }}
    >
      <table
        id={id}
        className={`cf-table ${className}`}
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          textAlign: 'left',
          fontSize: 'var(--cf-font-size-base)',
          fontFamily: 'var(--cf-font-sans)',
        }}
      >
        {children}
      </table>
    </div>
  )
}

export function TableHead({ children, className = '', style = {} }) {
  return (
    <thead
      className={`cf-table-head ${className}`}
      style={{
        background: 'var(--cf-bg-surface-elevated)',
        borderBottom: '1px solid var(--cf-border)',
        ...style,
      }}
    >
      {children}
    </thead>
  )
}

export function TableBody({ children, className = '', style = {} }) {
  return (
    <tbody className={`cf-table-body ${className}`} style={style}>
      {children}
    </tbody>
  )
}

export function TableRow({
  children,
  onClick,
  hoverable = true,
  className = '',
  style = {},
}) {
  return (
    <tr
      onClick={onClick}
      className={`cf-table-row ${hoverable ? 'cf-table-row-hoverable' : ''} ${className}`}
      style={{
        borderBottom: '1px solid var(--cf-border)',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'background var(--cf-transition-fast)',
        ...style,
      }}
      onMouseEnter={
        hoverable
          ? (e) => (e.currentTarget.style.background = 'var(--cf-bg-surface-hover)')
          : undefined
      }
      onMouseLeave={
        hoverable
          ? (e) => (e.currentTarget.style.background = 'transparent')
          : undefined
      }
    >
      {children}
    </tr>
  )
}

export function TableHeaderCell({
  children,
  align = 'left', // 'left' | 'center' | 'right'
  className = '',
  style = {},
}) {
  return (
    <th
      className={`cf-table-th ${className}`}
      style={{
        padding: 'var(--cf-space-3) var(--cf-space-4)',
        fontSize: 'var(--cf-font-size-xs)',
        fontWeight: 'var(--cf-font-weight-bold)',
        color: 'var(--cf-text-secondary)',
        textTransform: 'uppercase',
        letterSpacing: '0.06em',
        textAlign: align,
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      {children}
    </th>
  )
}

export function TableCell({
  children,
  align = 'left', // 'left' | 'center' | 'right'
  tabular = false,
  className = '',
  style = {},
}) {
  return (
    <td
      className={`cf-table-td ${tabular ? 'cf-num-tabular' : ''} ${className}`}
      style={{
        padding: 'var(--cf-space-3) var(--cf-space-4)',
        color: 'var(--cf-text-primary)',
        textAlign: align,
        fontVariantNumeric: tabular ? 'tabular-nums' : 'normal',
        ...style,
      }}
    >
      {children}
    </td>
  )
}
