from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
import statistics
from typing import Optional

from app.analytics.calculations import to_decimal
from app.analytics.domain import ATRResult, BollingerBandsResult, MACDResult


def calculate_sma(
    values: Sequence[Decimal | float | int | str],
    window: int,
) -> list[Optional[Decimal]]:
    """Calculate Simple Moving Average (SMA) over a specified rolling window.

    Args:
        values: Sequence of numerical values (e.g. closing prices).
        window: Number of periods in the rolling window (must be >= 1).

    Returns:
        list[Optional[Decimal]]: List of SMA values aligned with input sequence.
            Values during the warmup period (< window) are None.
    """
    if window < 1:
        raise ValueError("SMA window must be greater than or equal to 1")

    n = len(values)
    if n == 0:
        return []

    dec_values = [to_decimal(v) for v in values]
    result: list[Optional[Decimal]] = [None] * n

    if n < window:
        return result

    # Compute initial window sum
    window_sum = sum(dec_values[:window], Decimal("0"))
    dec_window = Decimal(str(window))
    result[window - 1] = (window_sum / dec_window).quantize(Decimal("0.0001"))

    # Slide window
    for i in range(window, n):
        window_sum += dec_values[i] - dec_values[i - window]
        result[i] = (window_sum / dec_window).quantize(Decimal("0.0001"))

    return result


def calculate_ema(
    values: Sequence[Decimal | float | int | str],
    window: int,
) -> list[Optional[Decimal]]:
    """Calculate Exponential Moving Average (EMA) over a specified window.

    Uses the initial SMA of the first `window` periods as the seed value,
    followed by the recursive formula:
        EMA_t = alpha * Value_t + (1 - alpha) * EMA_{t-1}
        where alpha = 2 / (window + 1)

    Args:
        values: Sequence of numerical values.
        window: Number of periods in the EMA window (must be >= 1).

    Returns:
        list[Optional[Decimal]]: List of EMA values aligned with input sequence.
    """
    if window < 1:
        raise ValueError("EMA window must be greater than or equal to 1")

    n = len(values)
    if n == 0:
        return []

    dec_values = [to_decimal(v) for v in values]
    result: list[Optional[Decimal]] = [None] * n

    if n < window:
        return result

    # Seed with SMA of first window
    initial_sma = sum(dec_values[:window], Decimal("0")) / Decimal(str(window))
    result[window - 1] = initial_sma.quantize(Decimal("0.0001"))

    alpha = Decimal("2") / Decimal(str(window + 1))
    one_minus_alpha = Decimal("1") - alpha

    current_ema = initial_sma
    for i in range(window, n):
        current_ema = (alpha * dec_values[i]) + (one_minus_alpha * current_ema)
        result[i] = current_ema.quantize(Decimal("0.0001"))

    return result


def calculate_rsi(
    values: Sequence[Decimal | float | int | str],
    period: int = 14,
) -> list[Optional[Decimal]]:
    """Calculate Relative Strength Index (RSI) using Wilder's smoothed moving average.

    Standard formula:
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss

    Args:
        values: Sequence of prices.
        period: Number of periods for RSI (typically 14).

    Returns:
        list[Optional[Decimal]]: RSI values in range [0, 100] aligned with input.
            Values during the initial warmup period (first `period` items) are None.
    """
    if period < 1:
        raise ValueError("RSI period must be greater than or equal to 1")

    n = len(values)
    if n == 0:
        return []

    result: list[Optional[Decimal]] = [None] * n
    if n <= period:
        return result

    dec_values = [to_decimal(v) for v in values]

    # Calculate price changes
    changes = [dec_values[i] - dec_values[i - 1] for i in range(1, n)]

    # Initial average gain and loss over the first `period` changes
    gains = [max(c, Decimal("0")) for c in changes[:period]]
    losses = [max(-c, Decimal("0")) for c in changes[:period]]

    avg_gain = sum(gains, Decimal("0")) / Decimal(str(period))
    avg_loss = sum(losses, Decimal("0")) / Decimal(str(period))

    # Compute RSI for index `period`
    if avg_loss == Decimal("0"):
        rsi_val = Decimal("100.00") if avg_gain > Decimal("0") else Decimal("50.00")
    else:
        rs = avg_gain / avg_loss
        rsi_val = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

    result[period] = rsi_val.quantize(Decimal("0.01"))

    # Wilder's smoothing for subsequent periods
    dec_period = Decimal(str(period))
    dec_period_minus_one = Decimal(str(period - 1))

    for i in range(period, len(changes)):
        change = changes[i]
        gain = max(change, Decimal("0"))
        loss = max(-change, Decimal("0"))

        avg_gain = ((avg_gain * dec_period_minus_one) + gain) / dec_period
        avg_loss = ((avg_loss * dec_period_minus_one) + loss) / dec_period

        if avg_loss == Decimal("0"):
            rsi_val = Decimal("100.00") if avg_gain > Decimal("0") else Decimal("50.00")
        else:
            rs = avg_gain / avg_loss
            rsi_val = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

        result[i + 1] = rsi_val.quantize(Decimal("0.01"))

    return result


def calculate_macd(
    values: Sequence[Decimal | float | int | str],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    timestamps: Optional[Sequence[datetime]] = None,
) -> MACDResult:
    """Calculate Moving Average Convergence Divergence (MACD).

    Components:
        MACD Line = Fast EMA - Slow EMA
        Signal Line = Signal EMA of MACD Line
        Histogram = MACD Line - Signal Line

    Args:
        values: Sequence of closing prices.
        fast: Fast EMA lookback window (default 12).
        slow: Slow EMA lookback window (default 26).
        signal: Signal EMA lookback window (default 9).
        timestamps: Optional list of observation timestamps.

    Returns:
        MACDResult: Dataclass containing macd_line, signal_line, and histogram lists.
    """
    if fast >= slow:
        raise ValueError("Fast period must be strictly less than slow period")

    n = len(values)
    if n == 0:
        return MACDResult(
            macd_line=[],
            signal_line=[],
            histogram=[],
            fast_period=fast,
            slow_period=slow,
            signal_period=signal,
            timestamps=list(timestamps) if timestamps else None,
        )

    fast_ema = calculate_ema(values, fast)
    slow_ema = calculate_ema(values, slow)

    # MACD Line is defined where slow_ema is defined (from slow - 1 onwards)
    macd_line: list[Optional[Decimal]] = [None] * n
    valid_macd_indices: list[int] = []
    valid_macd_values: list[Decimal] = []

    for i in range(n):
        f = fast_ema[i]
        s = slow_ema[i]
        if f is not None and s is not None:
            diff = (f - s).quantize(Decimal("0.0001"))
            macd_line[i] = diff
            valid_macd_indices.append(i)
            valid_macd_values.append(diff)

    # Signal Line: EMA of valid MACD values
    signal_line: list[Optional[Decimal]] = [None] * n
    histogram: list[Optional[Decimal]] = [None] * n

    if len(valid_macd_values) >= signal:
        raw_signal = calculate_ema(valid_macd_values, signal)
        for sub_idx, sig_val in enumerate(raw_signal):
            orig_idx = valid_macd_indices[sub_idx]
            signal_line[orig_idx] = sig_val
            if macd_line[orig_idx] is not None and sig_val is not None:
                histogram[orig_idx] = (macd_line[orig_idx] - sig_val).quantize(Decimal("0.0001"))

    return MACDResult(
        macd_line=macd_line,
        signal_line=signal_line,
        histogram=histogram,
        fast_period=fast,
        slow_period=slow,
        signal_period=signal,
        timestamps=list(timestamps) if timestamps else None,
    )


def calculate_bollinger_bands(
    values: Sequence[Decimal | float | int | str],
    window: int = 20,
    num_std: Decimal | float | int | str = Decimal("2.0"),
    timestamps: Optional[Sequence[datetime]] = None,
) -> BollingerBandsResult:
    """Calculate Bollinger Bands volatility envelope.

    Components:
        Middle Band = SMA(window)
        Upper Band = Middle Band + (num_std * Standard Deviation)
        Lower Band = Middle Band - (num_std * Standard Deviation)
        Bandwidth = ((Upper - Lower) / Middle) * 100
        %B = (Price - Lower) / (Upper - Lower)

    Args:
        values: Sequence of closing prices.
        window: Moving average rolling window (default 20).
        num_std: Standard deviation multiplier (default 2.0).
        timestamps: Optional observation timestamps.

    Returns:
        BollingerBandsResult: Dataclass with upper, middle, lower, bandwidth, and %B series.
    """
    if window < 1:
        raise ValueError("Bollinger Bands window must be >= 1")

    dec_num_std = to_decimal(num_std)
    n = len(values)
    if n == 0:
        return BollingerBandsResult(
            upper_band=[],
            middle_band=[],
            lower_band=[],
            bandwidth=[],
            percent_b=[],
            window=window,
            num_std=dec_num_std,
            timestamps=list(timestamps) if timestamps else None,
        )

    dec_values = [to_decimal(v) for v in values]
    middle_band = calculate_sma(dec_values, window)

    upper_band: list[Optional[Decimal]] = [None] * n
    lower_band: list[Optional[Decimal]] = [None] * n
    bandwidth: list[Optional[Decimal]] = [None] * n
    percent_b: list[Optional[Decimal]] = [None] * n

    if n < window:
        return BollingerBandsResult(
            upper_band=upper_band,
            middle_band=middle_band,
            lower_band=lower_band,
            bandwidth=bandwidth,
            percent_b=percent_b,
            window=window,
            num_std=dec_num_std,
            timestamps=list(timestamps) if timestamps else None,
        )

    for i in range(window - 1, n):
        slice_vals = [float(v) for v in dec_values[i - window + 1 : i + 1]]
        mid = middle_band[i]
        if mid is None:
            continue

        # Standard population deviation for Bollinger Bands
        stdev_val = Decimal(str(round(statistics.pstdev(slice_vals), 6)))
        band_spread = (dec_num_std * stdev_val).quantize(Decimal("0.0001"))

        upper = (mid + band_spread).quantize(Decimal("0.0001"))
        lower = (mid - band_spread).quantize(Decimal("0.0001"))
        upper_band[i] = upper
        lower_band[i] = lower

        # Bandwidth: ((Upper - Lower) / Middle) * 100
        if mid > Decimal("0"):
            bw = (((upper - lower) / mid) * Decimal("100")).quantize(Decimal("0.01"))
            bandwidth[i] = bw
        else:
            bandwidth[i] = Decimal("0.00")

        # %B: (Price - Lower) / (Upper - Lower)
        denom = upper - lower
        if denom > Decimal("0"):
            pct_b = ((dec_values[i] - lower) / denom).quantize(Decimal("0.0001"))
            percent_b[i] = pct_b
        else:
            percent_b[i] = Decimal("0.5000")

    return BollingerBandsResult(
        upper_band=upper_band,
        middle_band=middle_band,
        lower_band=lower_band,
        bandwidth=bandwidth,
        percent_b=percent_b,
        window=window,
        num_std=dec_num_std,
        timestamps=list(timestamps) if timestamps else None,
    )


def calculate_true_range(
    highs: Sequence[Decimal | float | int | str],
    lows: Sequence[Decimal | float | int | str],
    closes: Sequence[Decimal | float | int | str],
) -> list[Optional[Decimal]]:
    """Calculate True Range (TR) sequence across historical OHLC observations.

    Standard formula by J. Welles Wilder:
        For t = 0: TR_0 = High_0 - Low_0
        For t > 0: TR_t = max(High_t - Low_t, abs(High_t - Close_{t-1}), abs(Low_t - Close_{t-1}))

    Args:
        highs: Sequence of high prices.
        lows: Sequence of low prices.
        closes: Sequence of closing prices.

    Returns:
        list[Optional[Decimal]]: Aligned True Range series.
    """
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("High, Low, and Close sequences must have identical lengths")

    n = len(highs)
    if n == 0:
        return []

    dec_highs = [to_decimal(h) for h in highs]
    dec_lows = [to_decimal(l) for l in lows]
    dec_closes = [to_decimal(c) for c in closes]

    result: list[Optional[Decimal]] = [None] * n
    # Period 0: High - Low
    result[0] = (dec_highs[0] - dec_lows[0]).quantize(Decimal("0.0001"))

    for i in range(1, n):
        prev_close = dec_closes[i - 1]
        hl = dec_highs[i] - dec_lows[i]
        h_pc = abs(dec_highs[i] - prev_close)
        l_pc = abs(dec_lows[i] - prev_close)
        tr = max(hl, h_pc, l_pc)
        result[i] = tr.quantize(Decimal("0.0001"))

    return result


def calculate_atr(
    highs: Sequence[Decimal | float | int | str],
    lows: Sequence[Decimal | float | int | str],
    closes: Sequence[Decimal | float | int | str],
    period: int = 14,
    timestamps: Optional[Sequence[datetime]] = None,
) -> ATRResult:
    """Calculate Average True Range (ATR) using Wilder's smoothed moving average.

    Components:
        True Range = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))
        Initial ATR = SMA(True Range, period)
        Subsequent ATR = (PrevATR * (period - 1) + CurrentTR) / period
        ATR% = (ATR / Close) * 100

    Args:
        highs: Sequence of high prices.
        lows: Sequence of low prices.
        closes: Sequence of closing prices.
        period: Number of periods for smoothing (default 14).
        timestamps: Optional observation timestamps.

    Returns:
        ATRResult: Dataclass containing tr, atr, and atr_percent series.
    """
    if period < 1:
        raise ValueError("ATR period must be greater than or equal to 1")

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("High, Low, and Close sequences must have identical lengths")

    n = len(highs)
    if n == 0:
        return ATRResult(
            tr=[],
            atr=[],
            atr_percent=[],
            period=period,
            timestamps=list(timestamps) if timestamps else None,
        )

    tr_series = calculate_true_range(highs, lows, closes)
    atr_series: list[Optional[Decimal]] = [None] * n
    atr_pct_series: list[Optional[Decimal]] = [None] * n

    if n < period:
        return ATRResult(
            tr=tr_series,
            atr=atr_series,
            atr_percent=atr_pct_series,
            period=period,
            timestamps=list(timestamps) if timestamps else None,
        )

    dec_closes = [to_decimal(c) for c in closes]
    dec_period = Decimal(str(period))
    dec_period_minus_one = Decimal(str(period - 1))

    # Initial ATR seed at index period - 1
    seed_sum = sum((tr_series[i] for i in range(period) if tr_series[i] is not None), Decimal("0"))
    current_atr = seed_sum / dec_period
    atr_series[period - 1] = current_atr.quantize(Decimal("0.0001"))
    if dec_closes[period - 1] > Decimal("0"):
        atr_pct_series[period - 1] = ((current_atr / dec_closes[period - 1]) * Decimal("100")).quantize(Decimal("0.01"))
    else:
        atr_pct_series[period - 1] = Decimal("0.00")

    # Wilder's smoothing for subsequent periods
    for i in range(period, n):
        tr_val = tr_series[i]
        if tr_val is not None:
            current_atr = ((current_atr * dec_period_minus_one) + tr_val) / dec_period
            atr_series[i] = current_atr.quantize(Decimal("0.0001"))
            if dec_closes[i] > Decimal("0"):
                atr_pct_series[i] = ((current_atr / dec_closes[i]) * Decimal("100")).quantize(Decimal("0.01"))
            else:
                atr_pct_series[i] = Decimal("0.00")

    return ATRResult(
        tr=tr_series,
        atr=atr_series,
        atr_percent=atr_pct_series,
        period=period,
        timestamps=list(timestamps) if timestamps else None,
    )

