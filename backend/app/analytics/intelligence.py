from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from app.analytics.calculations import (
    calculate_returns,
    calculate_rolling_volatility,
    to_decimal,
)
from app.analytics.domain import (
    MarketIntelligenceSummary,
    MomentumState,
    TrendPosture,
    VolatilityRegime,
)
from app.analytics.indicators import (
    calculate_bollinger_bands,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)


def synthesize_market_intelligence(
    symbol: str,
    prices: Sequence[Decimal | float | int | str],
    timestamps: Optional[Sequence[datetime]] = None,
    annualize_factor: int = 252,
) -> MarketIntelligenceSummary:
    """Synthesize deterministic, explainable technical market intelligence.

    Combines trend structure, momentum oscillators, and volatility regimes
    into a calibrated 0-100 composite technical score and human-readable rationales.

    Args:
        symbol: The instrument symbol.
        prices: Chronological closing price sequence (oldest to newest).
        timestamps: Optional chronological observation timestamps.
        annualize_factor: Volatility annualization factor (252 for stocks, 365 for crypto).

    Returns:
        MarketIntelligenceSummary: Comprehensive intelligence summary.
    """
    clean_symbol = symbol.strip().upper()
    n = len(prices)

    if n == 0:
        return MarketIntelligenceSummary(
            symbol=clean_symbol,
            current_price=Decimal("0"),
            trend_posture=TrendPosture.NEUTRAL,
            momentum_state=MomentumState.NEUTRAL,
            volatility_regime=VolatilityRegime.NORMAL,
            composite_score=50,
            summary_verdict="Insufficient Data",
            rationales=["Insufficient historical price observations to compute market intelligence."],
            as_of=timestamps[-1] if timestamps else None,
            metrics={},
        )

    dec_prices = [to_decimal(p) for p in prices]
    current_price = dec_prices[-1]
    as_of = timestamps[-1] if timestamps and len(timestamps) == n else None

    # Compute technical indicators
    sma20 = calculate_sma(dec_prices, 20)
    sma50 = calculate_sma(dec_prices, 50)
    sma200 = calculate_sma(dec_prices, 200)
    rsi14 = calculate_rsi(dec_prices, 14)
    macd = calculate_macd(dec_prices, 12, 26, 9)
    bb = calculate_bollinger_bands(dec_prices, 20, Decimal("2.0"))

    returns = calculate_returns(dec_prices)
    vol = calculate_rolling_volatility(returns, window=30, annualize_factor=annualize_factor)

    rationales: list[str] = []
    score = 50

    # 1. Evaluate Trend Posture
    last_sma20 = sma20[-1] if sma20 else None
    last_sma50 = sma50[-1] if sma50 else None
    last_sma200 = sma200[-1] if sma200 else None

    # Check cross events (SMA50 vs SMA200 over last 5 bars)
    golden_cross = False
    death_cross = False
    if last_sma50 and last_sma200 and n >= 5:
        idx_prev = max(0, n - 5)
        prev_50 = sma50[idx_prev]
        prev_200 = sma200[idx_prev]
        if prev_50 and prev_200:
            if prev_50 <= prev_200 and last_sma50 > last_sma200:
                golden_cross = True
            elif prev_50 >= prev_200 and last_sma50 < last_sma200:
                death_cross = True

    if golden_cross:
        trend = TrendPosture.GOLDEN_CROSS
        score += 20
        rationales.append("Golden Cross detected: 50-period SMA crossed above 200-period SMA.")
    elif death_cross:
        trend = TrendPosture.DEATH_CROSS
        score -= 20
        rationales.append("Death Cross detected: 50-period SMA crossed below 200-period SMA.")
    elif last_sma50 and last_sma200:
        if current_price > last_sma20 > last_sma50 > last_sma200:  # type: ignore[operator]
            trend = TrendPosture.BULLISH
            score += 25
            pct_above_50 = ((current_price - last_sma50) / last_sma50 * Decimal("100")).quantize(Decimal("0.01"))
            rationales.append(f"Strong bullish alignment: Price is {pct_above_50}% above 50-period SMA and above 200-period SMA.")
        elif current_price < last_sma20 < last_sma50 < last_sma200:  # type: ignore[operator]
            trend = TrendPosture.BEARISH
            score -= 25
            pct_below_50 = ((last_sma50 - current_price) / last_sma50 * Decimal("100")).quantize(Decimal("0.01"))
            rationales.append(f"Strong bearish alignment: Price is {pct_below_50}% below 50-period SMA and below 200-period SMA.")
        elif current_price > last_sma50:
            trend = TrendPosture.MODERATELY_BULLISH
            score += 15
            rationales.append("Moderately bullish posture: Price trades above 50-period moving average.")
        elif current_price < last_sma50:
            trend = TrendPosture.MODERATELY_BEARISH
            score -= 15
            rationales.append("Moderately bearish posture: Price trades below 50-period moving average.")
        else:
            trend = TrendPosture.NEUTRAL
            rationales.append("Neutral trend posture: Moving averages are consolidating.")
    elif last_sma50:
        if current_price > last_sma50:
            trend = TrendPosture.MODERATELY_BULLISH
            score += 15
            rationales.append("Price is trading above 50-period moving average.")
        elif current_price < last_sma50:
            trend = TrendPosture.MODERATELY_BEARISH
            score -= 15
            rationales.append("Price is trading below 50-period moving average.")
        else:
            trend = TrendPosture.NEUTRAL
            rationales.append("Neutral trend consolidation near 50-period SMA.")
    elif last_sma20:
        if current_price > last_sma20:
            trend = TrendPosture.MODERATELY_BULLISH
            score += 10
            rationales.append("Price is trading above short-term 20-period moving average.")
        else:
            trend = TrendPosture.MODERATELY_BEARISH
            score -= 10
            rationales.append("Price is trading below short-term 20-period moving average.")
    else:
        trend = TrendPosture.NEUTRAL
        rationales.append("Short history: insufficient bars for moving average trend posture.")

    # 2. Evaluate Momentum State
    last_rsi = rsi14[-1] if rsi14 else None
    last_macd_hist = macd.histogram[-1] if macd.histogram else None

    if last_rsi is not None:
        if last_rsi >= Decimal("70.00"):
            momentum = MomentumState.OVERBOUGHT
            score += 5
            rationales.append(f"RSI is overbought at {last_rsi}, suggesting strong buying pressure with near-term pullback risk.")
        elif last_rsi <= Decimal("30.00"):
            momentum = MomentumState.OVERSOLD
            score -= 5
            rationales.append(f"RSI is oversold at {last_rsi}, indicating heavy selling pressure and potential exhaustion.")
        elif last_macd_hist and last_macd_hist > Decimal("0") and last_rsi >= Decimal("50.00"):
            momentum = MomentumState.BULLISH_MOMENTUM
            score += 15
            rationales.append(f"Positive momentum: RSI ({last_rsi}) > 50 with expanding MACD histogram (+{last_macd_hist}).")
        elif last_macd_hist and last_macd_hist < Decimal("0") and last_rsi < Decimal("50.00"):
            momentum = MomentumState.BEARISH_MOMENTUM
            score -= 15
            rationales.append(f"Negative momentum: RSI ({last_rsi}) < 50 with negative MACD histogram ({last_macd_hist}).")
        else:
            momentum = MomentumState.NEUTRAL
            rationales.append(f"Neutral momentum: RSI is balanced at {last_rsi}.")
    else:
        momentum = MomentumState.NEUTRAL
        rationales.append("Insufficient bars for RSI momentum analysis.")

    # 3. Evaluate Volatility Regime
    ann_vol_float = float(vol.annualized_volatility) * 100
    if ann_vol_float < 15.0:
        vol_regime = VolatilityRegime.LOW
        score += 5
        rationales.append(f"Low volatility regime ({ann_vol_float:.1f}% annualized): Orderly price action.")
    elif ann_vol_float <= 35.0:
        vol_regime = VolatilityRegime.NORMAL
        rationales.append(f"Normal volatility regime ({ann_vol_float:.1f}% annualized): Typical dispersion.")
    elif ann_vol_float <= 60.0:
        vol_regime = VolatilityRegime.HIGH
        score -= 5
        rationales.append(f"High volatility regime ({ann_vol_float:.1f}% annualized): Elevated variance and risk.")
    else:
        vol_regime = VolatilityRegime.EXTREME
        score -= 10
        rationales.append(f"Extreme volatility regime ({ann_vol_float:.1f}% annualized): Rapid market swings.")

    # Bollinger Bands Position Context
    last_bb_pct_b = bb.percent_b[-1] if bb.percent_b else None
    if last_bb_pct_b is not None:
        if last_bb_pct_b > Decimal("1.0"):
            rationales.append("Price is trading above the upper Bollinger Band (volatility breakout/stretched).")
        elif last_bb_pct_b < Decimal("0.0"):
            rationales.append("Price is trading below the lower Bollinger Band (oversold channel penetration).")

    # Clamp composite score to [0, 100]
    final_score = max(0, min(100, score))

    # Derive human-friendly verdict
    if final_score >= 75:
        verdict = "Strong Bullish Uptrend"
    elif final_score >= 60:
        verdict = "Moderate Bullish Bias"
    elif final_score <= 25:
        verdict = "Strong Bearish Downtrend"
    elif final_score <= 40:
        verdict = "Moderate Bearish Bias"
    else:
        if momentum == MomentumState.OVERSOLD:
            verdict = "Oversold Reversal Watch"
        elif momentum == MomentumState.OVERBOUGHT:
            verdict = "Overbought Momentum Watch"
        else:
            verdict = "Neutral Consolidation"

    metrics = {
        "current_price": float(current_price),
        "sma20": float(last_sma20) if last_sma20 else None,
        "sma50": float(last_sma50) if last_sma50 else None,
        "sma200": float(last_sma200) if last_sma200 else None,
        "rsi14": float(last_rsi) if last_rsi else None,
        "macd": float(macd.macd_line[-1]) if macd.macd_line and macd.macd_line[-1] else None,
        "macd_signal": float(macd.signal_line[-1]) if macd.signal_line and macd.signal_line[-1] else None,
        "macd_histogram": float(last_macd_hist) if last_macd_hist else None,
        "bollinger_upper": float(bb.upper_band[-1]) if bb.upper_band and bb.upper_band[-1] else None,
        "bollinger_middle": float(bb.middle_band[-1]) if bb.middle_band and bb.middle_band[-1] else None,
        "bollinger_lower": float(bb.lower_band[-1]) if bb.lower_band and bb.lower_band[-1] else None,
        "annualized_volatility": float(vol.annualized_volatility),
        "data_points": n,
    }

    return MarketIntelligenceSummary(
        symbol=clean_symbol,
        current_price=current_price,
        trend_posture=trend,
        momentum_state=momentum,
        volatility_regime=vol_regime,
        composite_score=final_score,
        summary_verdict=verdict,
        rationales=rationales,
        as_of=as_of,
        metrics=metrics,
    )
