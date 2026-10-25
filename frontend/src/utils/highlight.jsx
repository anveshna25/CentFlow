/**
 * Highlight matching query characters in a given text string.
 *
 * @param {string} text - Source text to display
 * @param {string} query - Search term to highlight
 * @returns {React.ReactNode} String with highlighted matching substrings
 */
export function highlightMatch(text, query) {
  if (!query || !text) return text

  const cleanQuery = query.trim()
  if (!cleanQuery) return text

  // Escape special regex characters
  const escaped = cleanQuery.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  const parts = String(text).split(regex)

  if (parts.length <= 1) return text

  return parts.map((part, index) => {
    if (part.toLowerCase() === cleanQuery.toLowerCase()) {
      return (
        <mark
          key={index}
          style={{
            backgroundColor: 'rgba(0, 229, 255, 0.22)',
            color: 'var(--cf-brand-cyan)',
            padding: '1px 3px',
            borderRadius: '2px',
            fontWeight: 700,
          }}
        >
          {part}
        </mark>
      )
    }
    return part
  })
}
