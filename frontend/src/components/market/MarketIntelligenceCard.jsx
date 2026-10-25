import { Card } from '../common/Card'
import { Badge } from '../common/Badge'

/**
 * CentFlow Market Intelligence Card
 *
 * Renders synthesized technical score, trend posture, momentum verdict,
 * volatility regime, deterministic rationales, and risk metrics.
 */
export function MarketIntelligenceCard({
  symbol = '',
  intelligence = null,
  returnsAnalysis = null,
  isLoading = false,
  id = 'cf-market-intelligence-card',
}) {
  if (isLoading) {
    return (
      <Card id={id} style={{ padding: 'var(--cf-space-5)', position: 'relative' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--cf-space-8)', color: 'var(--cf-brand-cyan)', fontSize: '13px', gap: '8px' }}>
          <span style={{ display: 'inline-block', width: '14px', height: '14px', border: '2px solid var(--cf-brand-cyan)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          Synthesizing market intelligence for {symbol}...
        </div>
      </Card>
    )
  }

  if (!intelligence) {
    return (
      <Card id={id} style={{ padding: 'var(--cf-space-5)' }}>
        <div style={{ color: 'var(--cf-text-muted)', fontSize: '13px', textAlign: 'center', padding: 'var(--cf-space-4)' }}>
          No market intelligence summary available for {symbol}. Run historical backfill to populate calculation engine.
        </div>
      </Card>
    )
  }

  const score = Number(intelligence.composite_score ?? 50)
  const trend = intelligence.trend_posture || 'Neutral'
  const momentum = intelligence.momentum_verdict || 'Neutral Momentum'
  const volatility = intelligence.volatility_regime || 'Normal Volatility'
  const rationales = intelligence.rationales || []

  // Score color gradient determination
  let scoreColor
  let scoreBg
  let scoreLabel

  if (score >= 70) {
    scoreColor = 'var(--cf-bullish)'
    scoreBg = 'rgba(16, 185, 129, 0.15)'
    scoreLabel = 'Strong Bullish'
  } else if (score >= 55) {
    scoreColor = 'var(--cf-brand-cyan)'
    scoreBg = 'rgba(6, 182, 212, 0.15)'
    scoreLabel = 'Bullish'
  } else if (score >= 45) {
    scoreColor = 'var(--cf-text-secondary)'
    scoreBg = 'rgba(148, 163, 184, 0.15)'
    scoreLabel = 'Neutral'
  } else if (score >= 30) {
    scoreColor = 'var(--cf-warning)'
    scoreBg = 'rgba(245, 158, 11, 0.15)'
    scoreLabel = 'Cautious / Weak'
  } else {
    scoreColor = 'var(--cf-bearish)'
    scoreBg = 'rgba(239, 68, 68, 0.15)'
    scoreLabel = 'Bearish'
  }

  // Trend badge variant
  const isTrendBull = trend.toLowerCase().includes('bull')
  const isTrendBear = trend.toLowerCase().includes('bear')
  const trendVariant = isTrendBull ? 'bullish' : isTrendBear ? 'bearish' : 'neutral'

  return (
    <Card
      id={id}
      style={{
        padding: 'var(--cf-space-5)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--cf-space-4)',
        background: 'var(--cf-bg-surface-elevated)',
        border: '1px solid var(--cf-border)',
        borderRadius: 'var(--cf-radius-lg)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
            Market Intelligence & Quantitative Posture
          </span>
          <Badge variant="brand" size="sm">
            AI & Indicators Engine
          </Badge>
        </div>
        {intelligence.as_of_date && (
          <span style={{ fontSize: '11px', color: 'var(--cf-text-muted)' }}>
            Calculated as of {new Date(intelligence.as_of_date).toLocaleDateString()}
          </span>
        )}
      </div>

      {/* Hero Metrics Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 'var(--cf-space-3)',
        }}
      >
        {/* Composite Score Card */}
        <div
          style={{
            background: 'var(--cf-bg-base)',
            border: `1px solid ${scoreColor}33`,
            borderRadius: 'var(--cf-radius-md)',
            padding: 'var(--cf-space-4)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
            Technical Score
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', margin: '8px 0' }}>
            <span style={{ fontSize: '28px', fontWeight: 800, color: scoreColor, letterSpacing: '-0.03em' }}>
              {score}
            </span>
            <span style={{ fontSize: '13px', color: 'var(--cf-text-muted)' }}>/ 100</span>
          </div>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              alignSelf: 'flex-start',
              padding: '2px 8px',
              borderRadius: 'var(--cf-radius-full)',
              background: scoreBg,
              color: scoreColor,
              fontSize: '11px',
              fontWeight: 700,
            }}
          >
            {scoreLabel}
          </div>
        </div>

        {/* Trend Posture Card */}
        <div
          style={{
            background: 'var(--cf-bg-base)',
            border: '1px solid var(--cf-border)',
            borderRadius: 'var(--cf-radius-md)',
            padding: 'var(--cf-space-4)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
            Trend Posture
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--cf-text-primary)', margin: '8px 0' }}>
            {trend}
          </div>
          <div>
            <Badge variant={trendVariant} size="sm">
              {isTrendBull ? '▲ Uptrend Alignment' : isTrendBear ? '▼ Downtrend Pressure' : '⯀ Sideways / Consolidation'}
            </Badge>
          </div>
        </div>

        {/* Momentum Verdict Card */}
        <div
          style={{
            background: 'var(--cf-bg-base)',
            border: '1px solid var(--cf-border)',
            borderRadius: 'var(--cf-radius-md)',
            padding: 'var(--cf-space-4)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
            Momentum State
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--cf-text-primary)', margin: '8px 0' }}>
            {momentum}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--cf-text-secondary)' }}>
            RSI & MACD Impulse
          </div>
        </div>

        {/* Volatility Regime Card */}
        <div
          style={{
            background: 'var(--cf-bg-base)',
            border: '1px solid var(--cf-border)',
            borderRadius: 'var(--cf-radius-md)',
            padding: 'var(--cf-space-4)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
            Volatility Regime
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: 'var(--cf-text-primary)', margin: '8px 0' }}>
            {volatility}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--cf-text-secondary)' }}>
            Bollinger Envelope Width
          </div>
        </div>
      </div>

      {/* Synthesis Verdict Callout */}
      {intelligence.verdict && (
        <div
          style={{
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.25)',
            borderRadius: 'var(--cf-radius-md)',
            padding: 'var(--cf-space-3) var(--cf-space-4)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '16px' }}>💡</span>
          <div style={{ fontSize: '13px', color: 'var(--cf-text-primary)', lineHeight: 1.5 }}>
            <span style={{ fontWeight: 700, marginRight: '6px' }}>Synthesis Verdict:</span>
            {intelligence.verdict}
          </div>
        </div>
      )}

      {/* Deterministic Rationales List */}
      {rationales.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--cf-text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Analytical Drivers & Factor Signals
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '8px' }}>
            {rationales.map((rat, i) => (
              <div
                key={i}
                style={{
                  background: 'var(--cf-bg-base)',
                  border: '1px solid var(--cf-border)',
                  borderRadius: 'var(--cf-radius-sm)',
                  padding: '8px 12px',
                  fontSize: '12px',
                  color: 'var(--cf-text-secondary)',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '8px',
                  lineHeight: 1.4,
                }}
              >
                <span style={{ color: 'var(--cf-brand-cyan)', fontWeight: 700 }}>•</span>
                <span>{rat}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk & Performance Distribution (if returnsAnalysis is available) */}
      {returnsAnalysis && (
        <div
          style={{
            borderTop: '1px solid var(--cf-border)',
            paddingTop: 'var(--cf-space-3)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: 'var(--cf-space-3)',
          }}
        >
          <div>
            <div style={{ fontSize: '10px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Period Return</div>
            <div
              style={{
                fontSize: '14px',
                fontWeight: 700,
                color: Number(returnsAnalysis.period_return?.percentage_change ?? 0) >= 0 ? 'var(--cf-bullish)' : 'var(--cf-bearish)',
              }}
            >
              {Number(returnsAnalysis.period_return?.percentage_change ?? 0) >= 0 ? '+' : ''}
              {Number(returnsAnalysis.period_return?.percentage_change ?? 0).toFixed(2)}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Annualized Volatility</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-text-primary)' }}>
              {(Number(returnsAnalysis.volatility?.annualized_volatility ?? 0) * 100).toFixed(1)}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Max Drawdown</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--cf-bearish)' }}>
              -{Math.abs(Number(returnsAnalysis.drawdown?.max_drawdown_percentage ?? 0)).toFixed(1)}%
            </div>
          </div>
          <div>
            <div style={{ fontSize: '10px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>Drawdown State</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: returnsAnalysis.drawdown?.is_recovered ? 'var(--cf-bullish)' : 'var(--cf-warning)' }}>
              {returnsAnalysis.drawdown?.is_recovered ? 'Recovered' : 'Underwater'}
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
