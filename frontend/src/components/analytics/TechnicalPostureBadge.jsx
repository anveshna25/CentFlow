import { Badge } from '../common/Badge'

/**
 * CentFlow Technical Posture & Intelligence Badge
 *
 * Normalizes backend TrendPosture, MomentumState, and Composite Score
 * into a standard, visual, accessible badge across all product views.
 *
 * @param {string|Object} posture - TrendPosture string (e.g. 'bullish', 'moderately_bearish') or MarketIntelligence object.
 * @param {number} [score] - Optional composite score (0-100).
 * @param {string} [size='sm'] - Badge size ('sm' | 'md' | 'lg').
 * @param {boolean} [showScore=false] - Whether to append the numeric composite score.
 * @param {string} [id] - Optional element ID for testing.
 */
export function TechnicalPostureBadge({
  posture = 'NEUTRAL',
  score = null,
  size = 'sm',
  showScore = false,
  id,
}) {
  // Extract string posture if passed an intelligence object
  let resolvedScore = score
  const postureStr =
    typeof posture === 'object' && posture !== null
      ? posture.trend_posture || posture.momentum_state || 'NEUTRAL'
      : String(posture || 'NEUTRAL')

  if (typeof posture === 'object' && posture !== null && resolvedScore === null && posture.composite_score !== undefined) {
    resolvedScore = Number(posture.composite_score)
  }

  const normalized = postureStr.toLowerCase().replace(/[\s-]/g, '_')

  let variant
  let label
  let icon

  if (normalized.includes('golden') || normalized === 'strong_bullish') {
    variant = 'bullish'
    label = 'Strong Bullish'
    icon = '▲▲'
  } else if (normalized.includes('bullish') || normalized === 'bull') {
    variant = 'bullish'
    label = normalized.includes('moderately') ? 'Mod. Bullish' : 'Bullish'
    icon = '▲'
  } else if (normalized.includes('death') || normalized === 'strong_bearish') {
    variant = 'bearish'
    label = 'Strong Bearish'
    icon = '▼▼'
  } else if (normalized.includes('bearish') || normalized === 'bear') {
    variant = 'bearish'
    label = normalized.includes('moderately') ? 'Mod. Bearish' : 'Bearish'
    icon = '▼'
  } else if (normalized === 'oversold') {
    variant = 'brand'
    label = 'Oversold (Value)'
    icon = '↺'
  } else if (normalized === 'overbought') {
    variant = 'warning'
    label = 'Overbought'
    icon = '⚡'
  } else {
    variant = 'neutral'
    label = 'Neutral Posture'
    icon = '■'
  }

  return (
    <Badge variant={variant} size={size} id={id}>
      <span style={{ fontSize: '10px', opacity: 0.9 }}>{icon}</span>
      <span>{label}</span>
      {showScore && resolvedScore !== null && !isNaN(resolvedScore) && (
        <span
          style={{
            marginLeft: '4px',
            paddingLeft: '4px',
            borderLeft: '1px solid currentColor',
            fontWeight: 700,
            opacity: 0.95,
          }}
        >
          {resolvedScore}
        </span>
      )}
    </Badge>
  )
}
