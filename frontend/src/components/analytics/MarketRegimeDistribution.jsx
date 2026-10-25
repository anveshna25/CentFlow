import { Card } from '../common/Card'
import { Badge } from '../common/Badge'

/**
 * CentFlow Market Trend & Volatility Regime Distribution Component
 *
 * Displays market-wide consensus across monitored benchmark assets,
 * including bullish/neutral/bearish distribution, volatility regimes,
 * and composite factor sentiment.
 */
export function MarketRegimeDistribution({
  intelligenceMap = {},
  isLoading = false,
  id = 'cf-market-regime-distribution',
}) {
  const items = Object.values(intelligenceMap).filter(Boolean)

  if (isLoading && items.length === 0) {
    return (
      <Card id={id} title="Market Trend & Volatility Regimes" subtitle="Analyzing cross-asset technical consensus">
        <div style={{ padding: 'var(--cf-space-6)', textAlign: 'center', color: 'var(--cf-brand-cyan)', fontSize: '13px' }}>
          Aggregating multi-asset factor postures...
        </div>
      </Card>
    )
  }

  // Calculate statistics across available intelligence reports
  let bullishCount = 0
  let bearishCount = 0
  let neutralCount = 0
  let totalScore = 0
  const volatilityCounts = { low: 0, normal: 0, high: 0, extreme: 0 }

  items.forEach((item) => {
    const posture = String(item.trend_posture || '').toLowerCase()
    if (posture.includes('bull') || posture.includes('golden')) {
      bullishCount += 1
    } else if (posture.includes('bear') || posture.includes('death')) {
      bearishCount += 1
    } else {
      neutralCount += 1
    }

    if (item.composite_score !== undefined) {
      totalScore += Number(item.composite_score)
    }

    const vol = String(item.volatility_regime || 'normal').toLowerCase()
    if (volatilityCounts[vol] !== undefined) {
      volatilityCounts[vol] += 1
    } else {
      volatilityCounts.normal += 1
    }
  })

  const count = items.length || 1
  const bullPct = Math.round((bullishCount / count) * 100)
  const bearPct = Math.round((bearishCount / count) * 100)
  const neutPct = Math.round((neutralCount / count) * 100)
  const avgScore = items.length ? Math.round(totalScore / items.length) : 55

  // Sentiment consensus classification
  let consensusLabel = 'Neutral / Balanced'
  let consensusVariant = 'neutral'
  if (bullPct >= 60) {
    consensusLabel = 'Broad Bullish Consensus'
    consensusVariant = 'bullish'
  } else if (bearPct >= 60) {
    consensusLabel = 'Broad Bearish Posture'
    consensusVariant = 'bearish'
  } else if (bullPct > bearPct) {
    consensusLabel = 'Moderately Constructive'
    consensusVariant = 'brand'
  } else if (bearPct > bullPct) {
    consensusLabel = 'Cautionary Drift'
    consensusVariant = 'warning'
  }

  return (
    <Card
      id={id}
      title="Market-Wide Factor & Trend Distribution"
      subtitle="Quantitative alignment across primary equity, ETF, and crypto benchmarks"
      action={
        <Badge variant={consensusVariant} size="sm">
          {consensusLabel}
        </Badge>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--cf-space-4)' }}>
        {/* Trend Posture Distribution Stacked Bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
            <span style={{ color: 'var(--cf-text-secondary)' }}>Trend Distribution</span>
            <div style={{ display: 'flex', gap: '12px', fontSize: '11px', fontWeight: 600 }}>
              <span style={{ color: 'var(--cf-bullish)' }}>▲ {bullPct}% Bullish</span>
              <span style={{ color: 'var(--cf-text-muted)' }}>■ {neutPct}% Neutral</span>
              <span style={{ color: 'var(--cf-bearish)' }}>▼ {bearPct}% Bearish</span>
            </div>
          </div>

          {/* Multi-segment distribution track */}
          <div
            style={{
              display: 'flex',
              height: '8px',
              borderRadius: 'var(--cf-radius-full)',
              overflow: 'hidden',
              background: 'var(--cf-bg-surface-elevated)',
            }}
          >
            <div
              style={{
                width: `${bullPct}%`,
                background: 'var(--cf-bullish)',
                transition: 'width var(--cf-transition-normal)',
              }}
              title={`Bullish: ${bullPct}%`}
            />
            <div
              style={{
                width: `${neutPct}%`,
                background: 'var(--cf-border-strong)',
                transition: 'width var(--cf-transition-normal)',
              }}
              title={`Neutral: ${neutPct}%`}
            />
            <div
              style={{
                width: `${bearPct}%`,
                background: 'var(--cf-bearish)',
                transition: 'width var(--cf-transition-normal)',
              }}
              title={`Bearish: ${bearPct}%`}
            />
          </div>
        </div>

        {/* 3 Metrics Grid: Composite Sentiment, Volatility Profile, Observation Depth */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 'var(--cf-space-3)',
            marginTop: 'var(--cf-space-1)',
          }}
        >
          {/* Average Sentiment Score */}
          <div
            style={{
              background: 'var(--cf-bg-base)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
              Consensus Factor Score
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
              <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--cf-text-primary)' }}>
                {avgScore}
              </span>
              <span style={{ fontSize: '12px', color: 'var(--cf-text-muted)' }}>/ 100</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-secondary)', marginTop: '2px' }}>
              {avgScore >= 60 ? 'Favorable Momentum' : avgScore <= 40 ? 'Defensive Stance' : 'Balanced Regime'}
            </div>
          </div>

          {/* Volatility Regime Breakdown */}
          <div
            style={{
              background: 'var(--cf-bg-base)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
              Volatility Regimes
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap' }}>
              <Badge variant="neutral" size="sm">
                Normal: {volatilityCounts.normal}
              </Badge>
              {volatilityCounts.low > 0 && (
                <Badge variant="brand" size="sm">
                  Low: {volatilityCounts.low}
                </Badge>
              )}
              {volatilityCounts.high > 0 && (
                <Badge variant="warning" size="sm">
                  High: {volatilityCounts.high}
                </Badge>
              )}
              {volatilityCounts.extreme > 0 && (
                <Badge variant="bearish" size="sm">
                  Extreme: {volatilityCounts.extreme}
                </Badge>
              )}
            </div>
          </div>

          {/* Benchmark Coverage */}
          <div
            style={{
              background: 'var(--cf-bg-base)',
              border: '1px solid var(--cf-border)',
              borderRadius: 'var(--cf-radius-md)',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--cf-text-muted)', textTransform: 'uppercase' }}>
              Monitored Universe
            </div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--cf-brand-cyan)', marginTop: '4px' }}>
              {items.length} Assets
            </div>
            <div style={{ fontSize: '11px', color: 'var(--cf-text-secondary)', marginTop: '2px' }}>
              Equities · Crypto · Benchmark ETFs
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
