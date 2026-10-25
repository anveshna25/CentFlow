from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
import math
import statistics
from typing import Optional

from app.analytics.domain import DrawdownMetric, PeriodReturn, PriceSeriesSummary, VolatilityMetrics


def to_decimal(value: float | int | str | Decimal) -> Decimal:
    """Helper ensuring value is a Decimal."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def calculate_price_change(
    current_price: Decimal | float,
    previous_price: Decimal | float,
) -> tuple[Decimal, Decimal]:
    """Calculate absolute and percentage price change.

    Returns:
        tuple[Decimal, Decimal]: (absolute_change, percentage_change)
    """
    curr = to_decimal(current_price)
    prev = to_decimal(previous_price)

    absolute = (curr - prev).quantize(Decimal("0.0001"))
    if prev == Decimal("0"):
        return absolute, Decimal("0.0000")

    pct = ((absolute / prev) * Decimal("100")).quantize(Decimal("0.0001"))
    return absolute, pct


def calculate_returns(prices: Sequence[Decimal | float]) -> list[Decimal]:
    """Calculate simple period-over-period returns: (P_t - P_{t-1}) / P_{t-1}."""
    if len(prices) < 2:
        return []

    returns: list[Decimal] = []
    for i in range(1, len(prices)):
        prev = to_decimal(prices[i - 1])
        curr = to_decimal(prices[i])
        if prev == Decimal("0"):
            returns.append(Decimal("0.000000"))
        else:
            ret = ((curr - prev) / prev).quantize(Decimal("0.000001"))
            returns.append(ret)
    return returns


def calculate_log_returns(prices: Sequence[Decimal | float]) -> list[Decimal]:
    """Calculate continuous logarithmic returns: ln(P_t / P_{t-1})."""
    if len(prices) < 2:
        return []

    log_returns: list[Decimal] = []
    for i in range(1, len(prices)):
        prev = float(prices[i - 1])
        curr = float(prices[i])
        if prev <= 0 or curr <= 0:
            log_returns.append(Decimal("0.000000"))
        else:
            log_ret = math.log(curr / prev)
            log_returns.append(Decimal(str(round(log_ret, 6))))
    return log_returns


def calculate_period_return(
    prices: Sequence[Decimal | float],
    timestamps: Optional[Sequence[datetime]] = None,
) -> Optional[PeriodReturn]:
    """Calculate overall performance metrics across a full price sequence."""
    if len(prices) < 2:
        return None

    start_p = to_decimal(prices[0])
    end_p = to_decimal(prices[-1])
    abs_change, pct_change = calculate_price_change(end_p, start_p)

    log_ret = None
    if start_p > Decimal("0") and end_p > Decimal("0"):
        log_val = math.log(float(end_p) / float(start_p))
        log_ret = Decimal(str(round(log_val, 6)))

    start_time = timestamps[0] if timestamps and len(timestamps) > 0 else None
    end_time = timestamps[-1] if timestamps and len(timestamps) > 0 else None

    return PeriodReturn(
        start_price=start_p,
        end_price=end_p,
        absolute_change=abs_change,
        percentage_change=pct_change,
        log_return=log_ret,
        start_time=start_time,
        end_time=end_time,
    )


def calculate_rolling_volatility(
    returns: Sequence[Decimal | float],
    window: Optional[int] = None,
    annualize_factor: int = 252,
) -> VolatilityMetrics:
    """Calculate sample standard deviation and annualized volatility.

    Args:
        returns: Sequence of periodic fractional returns.
        window: Optional rolling lookback sample size.
        annualize_factor: Scaling factor (252 for trading days, 365 for crypto).
    """
    clean_returns = [float(r) for r in returns]
    if window and window > 0 and len(clean_returns) > window:
        clean_returns = clean_returns[-window:]

    n = len(clean_returns)
    if n < 2:
        return VolatilityMetrics(
            sample_std=Decimal("0.000000"),
            annualized_volatility=Decimal("0.000000"),
            annualize_factor=annualize_factor,
            sample_count=n,
        )

    sample_std = statistics.stdev(clean_returns)
    annualized = sample_std * math.sqrt(annualize_factor)

    return VolatilityMetrics(
        sample_std=Decimal(str(round(sample_std, 6))),
        annualized_volatility=Decimal(str(round(annualized, 6))),
        annualize_factor=annualize_factor,
        sample_count=n,
    )


def calculate_drawdowns(prices: Sequence[Decimal | float]) -> DrawdownMetric:
    """Compute maximum peak-to-trough drawdown across a price series."""
    if not prices:
        return DrawdownMetric(
            peak_price=Decimal("0"),
            trough_price=Decimal("0"),
            max_drawdown_amount=Decimal("0"),
            max_drawdown_pct=Decimal("0.00"),
            peak_index=0,
            trough_index=0,
            is_recovered=True,
        )

    peak = to_decimal(prices[0])
    peak_idx = 0

    max_dd_amount = Decimal("0")
    max_dd_pct = Decimal("0.00")
    max_peak = peak
    max_trough = peak
    max_peak_idx = 0
    max_trough_idx = 0

    for i, p in enumerate(prices):
        price = to_decimal(p)
        if price > peak:
            peak = price
            peak_idx = i

        dd_amount = peak - price
        if peak > Decimal("0"):
            dd_pct = (dd_amount / peak) * Decimal("100")
        else:
            dd_pct = Decimal("0.00")

        if dd_amount > max_dd_amount:
            max_dd_amount = dd_amount
            max_dd_pct = dd_pct
            max_peak = peak
            max_trough = price
            max_peak_idx = peak_idx
            max_trough_idx = i

    is_recovered = to_decimal(prices[-1]) >= max_peak

    return DrawdownMetric(
        peak_price=max_peak,
        trough_price=max_trough,
        max_drawdown_amount=max_dd_amount.quantize(Decimal("0.0001")),
        max_drawdown_pct=max_dd_pct.quantize(Decimal("0.01")),
        peak_index=max_peak_idx,
        trough_index=max_trough_idx,
        is_recovered=is_recovered,
    )


def calculate_price_summary(prices: Sequence[Decimal | float]) -> Optional[PriceSeriesSummary]:
    """Compute summary statistics (min, max, mean, median) for a price series."""
    if not prices:
        return None

    dec_prices = [to_decimal(p) for p in prices]
    float_prices = [float(p) for p in dec_prices]

    return PriceSeriesSummary(
        current_price=dec_prices[-1],
        mean_price=Decimal(str(round(statistics.mean(float_prices), 4))),
        median_price=Decimal(str(round(statistics.median(float_prices), 4))),
        min_price=min(dec_prices),
        max_price=max(dec_prices),
        data_points=len(dec_prices),
    )
