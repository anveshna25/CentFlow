from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
import math
import statistics
from typing import Optional

from app.analytics.domain import (
    BenchmarkMetrics,
    DrawdownMetric,
    PeriodReturn,
    PriceSeriesSummary,
    RiskAdjustedMetrics,
    VolatilityMetrics,
)


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


def prepare_validated_series(
    prices: Sequence[Decimal | float],
    timestamps: Optional[Sequence[datetime]] = None,
) -> tuple[list[Decimal], list[datetime]]:
    """Validate, sort, and deduplicate price series while preserving precision and handling gaps.

    Filters out invalid/zero/negative prices, deduplicates same-day/timestamp observations
    (taking the latest), sorts chronologically, and ensures aligned timestamps.
    """
    if not prices:
        return [], []

    raw_timestamps: list[datetime] = (
        list(timestamps)
        if timestamps and len(timestamps) == len(prices)
        else [datetime.fromtimestamp(i * 86400, tz=timezone.utc) for i in range(len(prices))]
    )

    valid_pairs: list[tuple[datetime, Decimal]] = []
    for t, p in zip(raw_timestamps, prices):
        if p is None or t is None:
            continue
        try:
            dec_p = to_decimal(p)
            if dec_p > Decimal("0"):
                valid_pairs.append((t, dec_p))
        except Exception:
            continue

    if not valid_pairs:
        return [], []

    # Sort chronologically by timestamp
    valid_pairs.sort(key=lambda x: x[0])

    # Deduplicate matching timestamps (retain last observation)
    deduped: dict[datetime, Decimal] = {}
    for t, p in valid_pairs:
        deduped[t] = p

    sorted_times = sorted(deduped.keys())
    sorted_prices = [deduped[t] for t in sorted_times]

    return sorted_prices, sorted_times


def calculate_downside_deviation(
    returns: Sequence[Decimal | float],
    mar: float = 0.0,
    annualize_factor: int = 252,
) -> Decimal:
    """Calculate sample downside standard deviation below minimum acceptable return (MAR)."""
    clean_returns = [float(r) for r in returns]
    if len(clean_returns) < 2:
        return Decimal("0.000000")

    underperform = [min(0.0, r - mar) ** 2 for r in clean_returns]
    downside_var = sum(underperform) / len(clean_returns)
    downside_dev = math.sqrt(downside_var) * math.sqrt(annualize_factor)
    return Decimal(str(round(downside_dev, 6)))


def calculate_risk_adjusted_metrics(
    prices: Sequence[Decimal | float],
    returns: Sequence[Decimal | float],
    volatility: VolatilityMetrics,
    drawdown: DrawdownMetric,
    risk_free_rate: float = 0.0,
    annualize_factor: int = 252,
) -> RiskAdjustedMetrics:
    """Compute risk-adjusted ratios: Sharpe, Sortino, Calmar, win rate, and downside metrics."""
    clean_returns = [float(r) for r in returns]
    total_periods = len(clean_returns)

    if total_periods == 0 or len(prices) < 2:
        zero_dec = Decimal("0.000000")
        return RiskAdjustedMetrics(
            annualized_return=zero_dec,
            cagr=zero_dec,
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            downside_deviation=zero_dec,
            win_rate=zero_dec,
            best_return=zero_dec,
            worst_return=zero_dec,
            positive_periods=0,
            negative_periods=0,
            total_periods=0,
        )

    pos_count = sum(1 for r in clean_returns if r > 0)
    neg_count = sum(1 for r in clean_returns if r < 0)
    win_rate = Decimal(str(round((pos_count / total_periods) * 100, 2)))
    best_ret = Decimal(str(round(max(clean_returns) * 100, 2)))
    worst_ret = Decimal(str(round(min(clean_returns) * 100, 2)))

    # Annualized return and CAGR calculation
    start_p = float(prices[0])
    end_p = float(prices[-1])
    total_return = (end_p - start_p) / start_p if start_p > 0 else 0.0

    years = total_periods / float(annualize_factor)
    if years > 0 and (1.0 + total_return) > 0:
        cagr = ((1.0 + total_return) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr = (total_return * (annualize_factor / total_periods)) * 100.0

    ann_ret = statistics.mean(clean_returns) * float(annualize_factor) * 100.0
    ann_ret_dec = Decimal(str(round(ann_ret, 4)))
    cagr_dec = Decimal(str(round(cagr, 4)))

    ann_vol = float(volatility.annualized_volatility)
    sharpe = None
    if ann_vol > 0:
        sharpe_val = (ann_ret - (risk_free_rate * 100.0)) / (ann_vol * 100.0)
        sharpe = Decimal(str(round(sharpe_val, 4)))

    downside_dev = calculate_downside_deviation(returns, mar=risk_free_rate, annualize_factor=annualize_factor)
    downside_float = float(downside_dev)
    sortino = None
    if downside_float > 0:
        sortino_val = (ann_ret - (risk_free_rate * 100.0)) / (downside_float * 100.0)
        sortino = Decimal(str(round(sortino_val, 4)))

    max_dd_pct = float(drawdown.max_drawdown_pct)
    calmar = None
    if max_dd_pct > 0:
        calmar = Decimal(str(round(cagr / max_dd_pct, 4)))

    return RiskAdjustedMetrics(
        annualized_return=ann_ret_dec,
        cagr=cagr_dec,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        downside_deviation=downside_dev,
        win_rate=win_rate,
        best_return=best_ret,
        worst_return=worst_ret,
        positive_periods=pos_count,
        negative_periods=neg_count,
        total_periods=total_periods,
    )


def align_price_series(
    asset_prices: Sequence[Decimal | float],
    asset_times: Sequence[datetime],
    benchmark_prices: Sequence[Decimal | float],
    benchmark_times: Sequence[datetime],
) -> tuple[list[Decimal], list[Decimal], list[datetime]]:
    """Align asset and benchmark series on matching trading days/timestamps.

    Handles non-trading gaps, differing exchange calendars, and weekend/crypto differences
    by taking the intersection of calendar dates (normalized to YYYY-MM-DD).
    """
    if not asset_prices or not benchmark_prices:
        return [], [], []

    asset_map: dict[str, tuple[Decimal, datetime]] = {}
    for p, t in zip(asset_prices, asset_times):
        date_key = t.strftime("%Y-%m-%d")
        asset_map[date_key] = (to_decimal(p), t)

    bench_map: dict[str, tuple[Decimal, datetime]] = {}
    for p, t in zip(benchmark_prices, benchmark_times):
        date_key = t.strftime("%Y-%m-%d")
        bench_map[date_key] = (to_decimal(p), t)

    common_dates = sorted(set(asset_map.keys()).intersection(set(bench_map.keys())))
    if not common_dates:
        return [], [], []

    aligned_asset = [asset_map[d][0] for d in common_dates]
    aligned_bench = [bench_map[d][0] for d in common_dates]
    aligned_times = [asset_map[d][1] for d in common_dates]

    return aligned_asset, aligned_bench, aligned_times


def calculate_benchmark_metrics(
    benchmark_symbol: str,
    asset_prices: Sequence[Decimal | float],
    benchmark_prices: Sequence[Decimal | float],
    annualize_factor: int = 252,
) -> BenchmarkMetrics:
    """Compute relative performance, beta, alpha, correlation, tracking error, and capture ratios against a benchmark."""
    clean_sym = benchmark_symbol.strip().upper()
    if len(asset_prices) < 2 or len(benchmark_prices) < 2:
        zero_dec = Decimal("0.00")
        return BenchmarkMetrics(
            benchmark_symbol=clean_sym,
            benchmark_return=zero_dec,
            excess_return=zero_dec,
            beta=None,
            alpha=None,
            correlation=None,
            r_squared=None,
            tracking_error=None,
            information_ratio=None,
            aligned_periods=min(len(asset_prices), len(benchmark_prices)),
        )

    r_asset = calculate_returns(asset_prices)
    r_bench = calculate_returns(benchmark_prices)
    n = min(len(r_asset), len(r_bench))
    if n < 2:
        zero_dec = Decimal("0.00")
        return BenchmarkMetrics(
            benchmark_symbol=clean_sym,
            benchmark_return=zero_dec,
            excess_return=zero_dec,
            beta=None,
            alpha=None,
            correlation=None,
            r_squared=None,
            tracking_error=None,
            information_ratio=None,
            aligned_periods=n,
        )

    a_rets = [float(r) for r in r_asset[:n]]
    b_rets = [float(r) for r in r_bench[:n]]

    # Period returns
    a_start, a_end = float(asset_prices[0]), float(asset_prices[-1])
    b_start, b_end = float(benchmark_prices[0]), float(benchmark_prices[-1])

    asset_total_ret = ((a_end - a_start) / a_start * 100.0) if a_start > 0 else 0.0
    bench_total_ret = ((b_end - b_start) / b_start * 100.0) if b_start > 0 else 0.0
    excess_ret = asset_total_ret - bench_total_ret

    mean_a = statistics.mean(a_rets)
    mean_b = statistics.mean(b_rets)
    var_b = statistics.variance(b_rets) if n > 1 else 0.0
    std_a = statistics.stdev(a_rets) if n > 1 else 0.0
    std_b = statistics.stdev(b_rets) if n > 1 else 0.0

    cov_ab = sum((a_rets[i] - mean_a) * (b_rets[i] - mean_b) for i in range(n)) / (n - 1)

    beta = None
    if var_b > 0:
        beta = Decimal(str(round(cov_ab / var_b, 4)))

    correlation = None
    r_squared = None
    if std_a > 0 and std_b > 0:
        corr_val = cov_ab / (std_a * std_b)
        corr_val = max(-1.0, min(1.0, corr_val))
        correlation = Decimal(str(round(corr_val, 4)))
        r_squared = Decimal(str(round(corr_val ** 2, 4)))

    alpha = None
    if beta is not None:
        # Annualized Jensen's alpha
        ann_a = mean_a * float(annualize_factor) * 100.0
        ann_b = mean_b * float(annualize_factor) * 100.0
        alpha_val = ann_a - (float(beta) * ann_b)
        alpha = Decimal(str(round(alpha_val, 4)))

    # Tracking error & Information Ratio
    diffs = [a_rets[i] - b_rets[i] for i in range(n)]
    tracking_err_val = (statistics.stdev(diffs) * math.sqrt(annualize_factor) * 100.0) if n > 1 else 0.0
    tracking_error = Decimal(str(round(tracking_err_val, 4)))

    info_ratio = None
    if tracking_err_val > 0:
        info_ratio = Decimal(str(round(excess_ret / tracking_err_val, 4)))

    # Up/Down capture ratios
    up_periods = [i for i in range(n) if b_rets[i] > 0]
    down_periods = [i for i in range(n) if b_rets[i] < 0]

    up_capture = None
    if up_periods:
        avg_a_up = statistics.mean([a_rets[i] for i in up_periods])
        avg_b_up = statistics.mean([b_rets[i] for i in up_periods])
        if avg_b_up != 0:
            up_capture = Decimal(str(round((avg_a_up / avg_b_up) * 100.0, 2)))

    down_capture = None
    if down_periods:
        avg_a_down = statistics.mean([a_rets[i] for i in down_periods])
        avg_b_down = statistics.mean([b_rets[i] for i in down_periods])
        if avg_b_down != 0:
            down_capture = Decimal(str(round((avg_a_down / avg_b_down) * 100.0, 2)))

    return BenchmarkMetrics(
        benchmark_symbol=clean_sym,
        benchmark_return=Decimal(str(round(bench_total_ret, 2))),
        excess_return=Decimal(str(round(excess_ret, 2))),
        beta=beta,
        alpha=alpha,
        correlation=correlation,
        r_squared=r_squared,
        tracking_error=tracking_error,
        information_ratio=info_ratio,
        up_capture=up_capture,
        down_capture=down_capture,
        aligned_periods=n,
    )
