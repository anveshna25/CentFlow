# CentFlow Analytics & Quantitative Intelligence Architecture

## 1. Overview & Architectural Principles

CentFlow's analytics engine transforms raw historical and real-time market data into deterministic, explainable, and testable financial intelligence.

In accordance with CentFlow's architecture:

```text
External Market Data
        ↓
Provider Adapters
        ↓
Market Data Engine (Ingestion & Persistence)
        ↓
Analytics Engine (`app/analytics/`)
        ↓
Analytics Service (`app/services/analytics.py`)
        ↓
FastAPI Routes (`app/api/routes/analytics.py`)
        ↓
React Product Experience
```

### Core Principles

1. **Deterministic & Explainable:** Analytical results are rooted in pure mathematical formulas. Every output can be traced directly to input observations without opaque black-box heuristics or arbitrary predictions.
2. **Precision & Numerical Safety:** Monetary calculations and ratios enforce bounded precision (using Python `Decimal` where appropriate) and explicitly guard against division-by-zero or logarithmic domain violations.
3. **Decoupled from Frameworks:** The analytics domain and calculations layer (`app/analytics/`) has zero dependencies on FastAPI, HTTP requests, database models, or React.
4. **Resilient Under Sparse Data:** All calculation routines gracefully handle edge cases such as empty series, single-period observations, and non-positive prices.

---

## 2. Directory Structure

```text
backend/app/analytics/
├── __init__.py           # Public exports for domain contracts, calculations, and indicators
├── domain.py             # Analytical value objects, metrics, indicator results, and observation windows
├── calculations.py       # Core deterministic price, return, volatility, and drawdown formulas
└── indicators.py         # Modular technical indicator algorithms (SMA, EMA, RSI, MACD, Bollinger Bands)
```

---

## 3. Analytics Domain Models (`app/analytics/domain.py`)

The analytics domain defines the data structures produced by calculations:

### `CalculationPeriod`
Standardized observation windows for performance and indicator calculations:
- `1d`: 1 Day
- `1w`: 1 Week
- `1m`: 1 Month
- `3m`: 3 Months
- `6m`: 6 Months
- `1y`: 1 Year
- `ytd`: Year to Date
- `all`: Full available history

### `PeriodReturn`
Captures absolute, relative, and logarithmic performance over an observation period:
- `start_price`: Initial price observation.
- `end_price`: Terminal price observation.
- `absolute_change`: Dollar/unit change ($P_{end} - P_{start}$).
- `percentage_change`: Relative percent change ($\frac{P_{end} - P_{start}}{P_{start}} \times 100$).
- `log_return`: Continuously compounded return ($\ln(P_{end} / P_{start})$).
- `start_time` / `end_time`: Optional timestamp bounds.

### `VolatilityMetrics`
Measures dispersion and variability of periodic returns:
- `sample_std`: Sample standard deviation of periodic returns.
- `annualized_volatility`: Scaled volatility ($s \times \sqrt{\text{factor}}$).
- `annualize_factor`: 252 for equity trading days, 365 for 24/7 crypto markets.
- `sample_count`: Number of periodic returns evaluated.

### `DrawdownMetric`
Identifies the maximum peak-to-trough decline across a series:
- `peak_price`: Highest preceding price level.
- `trough_price`: Lowest price level during the drawdown.
- `max_drawdown_amount`: Absolute decline ($Peak - Trough$).
- `max_drawdown_pct`: Percentage decline ($\frac{Peak - Trough}{Peak} \times 100$).
- `peak_index` / `trough_index`: Sequence positions of peak and trough.
- `is_recovered`: Whether the current terminal price has reached or exceeded the peak.

### `PriceSeriesSummary`
Fundamental distribution statistics for a price series:
- `current_price`: Latest observation.
- `mean_price`: Arithmetic average price.
- `median_price`: Median price.
- `min_price` / `max_price`: Range bounds.
- `data_points`: Total observation count.

### `IndicatorSeries`
Generic single-component time series with warmup period representation (`None` during warmup).

### `MACDResult`
Moving Average Convergence Divergence component series:
- `macd_line`: Fast EMA minus Slow EMA.
- `signal_line`: Exponential moving average of the MACD line.
- `histogram`: MACD line minus Signal line.
- `fast_period` / `slow_period` / `signal_period`: Configured parameters (defaults: 12, 26, 9).

### `BollingerBandsResult`
Bollinger Bands volatility envelope component series:
- `upper_band`: Middle band plus $k \times \sigma$.
- `middle_band`: Simple moving average.
- `lower_band`: Middle band minus $k \times \sigma$.
- `bandwidth`: Percentage band spread relative to middle band: $\frac{\text{Upper} - \text{Lower}}{\text{Middle}} \times 100$.
- `percent_b`: Relative position within the bands: $\frac{\text{Price} - \text{Lower}}{\text{Upper} - \text{Lower}}$.
- `window` / `num_std`: Configured window and standard deviation multiplier (defaults: 20, 2.0).

---

## 4. Quantitative Calculations (`app/analytics/calculations.py`)

### 1. Price Change
$$ \Delta P = P_{\text{current}} - P_{\text{previous}} $$
$$ \% \Delta P = \frac{\Delta P}{P_{\text{previous}}} \times 100 $$
*Safety:* If $P_{\text{previous}} = 0$, percentage change defaults to `0.0000%`.

### 2. Periodic Simple Returns
$$ R_t = \frac{P_t - P_{t-1}}{P_{t-1}} $$
Evaluates period-over-period returns across a price series of length $N \ge 2$, producing $N - 1$ return observations.

### 3. Logarithmic Returns
$$ r_t = \ln\left(\frac{P_t}{P_{t-1}}\right) $$
*Safety:* Non-positive prices are clipped with zero return to prevent domain math errors.

### 4. Rolling & Annualized Volatility
Sample standard deviation of returns:
$$ s = \sqrt{\frac{1}{n-1} \sum_{i=1}^n (R_i - \bar{R})^2} $$
Annualized volatility:
$$ \sigma_{\text{ann}} = s \times \sqrt{F} $$
where $F = 252$ (standard trading days) or custom lookback factor.

### 5. Maximum Drawdown (MDD)
Computes cumulative maximum $M_t = \max_{0 \le i \le t} P_i$ and drawdown $D_t = M_t - P_t$:
$$ \text{MDD} = \max_t D_t $$
Tracks peak and trough index coordinates and terminal recovery status.

---

## 5. Technical Indicators Engine (`app/analytics/indicators.py`)

### 1. Simple Moving Average (SMA)
For window $W$:
$$ \text{SMA}_t = \frac{1}{W} \sum_{i=t-W+1}^t P_i \quad \text{for } t \ge W - 1 $$
Values for $t < W - 1$ are returned as `None` (warmup period).

### 2. Exponential Moving Average (EMA)
Multiplier:
$$ \alpha = \frac{2}{W + 1} $$
Initial seed at $t = W - 1$ uses $\text{SMA}_W$. Subsequent values:
$$ \text{EMA}_t = \alpha \times P_t + (1 - \alpha) \times \text{EMA}_{t-1} $$

### 3. Relative Strength Index (RSI)
J. Welles Wilder Jr.'s smoothed RSI over period $N$ (default 14):
Initial averages over first $N$ price changes:
$$ AG_N = \frac{1}{N} \sum G_i, \quad AL_N = \frac{1}{N} \sum L_i $$
Wilder's smoothing for subsequent periods:
$$ AG_t = \frac{AG_{t-1} \times (N - 1) + G_t}{N}, \quad AL_t = \frac{AL_{t-1} \times (N - 1) + L_t}{N} $$
Relative Strength & Index:
$$ RS_t = \frac{AG_t}{AL_t}, \quad \text{RSI}_t = 100 - \left(\frac{100}{1 + RS_t}\right) $$
Boundary cases ($AL_t = 0$) default safely to $100.00$ ($AG_t > 0$) or $50.00$ ($AG_t = 0$).

### 4. Moving Average Convergence Divergence (MACD)
Standard parameters: fast=12, slow=26, signal=9.
- $\text{MACD}_t = \text{EMA}_{12}(P)_t - \text{EMA}_{26}(P)_t$
- $\text{Signal}_t = \text{EMA}_9(\text{MACD})_t$
- $\text{Histogram}_t = \text{MACD}_t - \text{Signal}_t$

### 5. Bollinger Bands
Window $W = 20$, standard deviation multiplier $k = 2.0$:
- $\text{Middle}_t = \text{SMA}_{20}(P)_t$
- $\text{Upper}_t = \text{Middle}_t + k \times \sigma_t$
- $\text{Lower}_t = \text{Middle}_t - k \times \sigma_t$
- $\text{Bandwidth}_t = \frac{\text{Upper}_t - \text{Lower}_t}{\text{Middle}_t} \times 100$
- $\%B_t = \frac{P_t - \text{Lower}_t}{\text{Upper}_t - \text{Lower}_t}$

---

## 6. Analytics Service Layer (`app/services/analytics.py`)

The `AnalyticsService` coordinates data access and high-level analytical computations:

- **Data Sources:** Prioritizes persisted database bars via `PriceRepository` when available, seamlessly falling back to cached external provider data via `MarketDataService`.
- **Primary Capabilities:**
  - `get_price_series(symbol, interval, lookback_days)`: Chronological price and timestamp series.
  - `get_price_summary(symbol, interval, lookback_days)`: Min, max, mean, median, and counts.
  - `get_performance_metrics(symbol, interval, lookback_days)`: Period returns, rolling volatility, drawdowns.
  - `get_technical_indicators(symbol, interval, lookback_days, ...)`: Parameterized SMAs, EMAs, RSI, MACD, and Bollinger Bands.
  - `get_market_intelligence(symbol, interval, lookback_days)`: Complete explainable market intelligence report.

---

## 7. Deterministic Market Intelligence Engine (`app/analytics/intelligence.py`)

Synthesizes multiple technical dimensions into an explainable, rule-based intelligence report:

### 1. Trend Posture
Classifies directional alignment of the asset:
- `bullish`: $P > \text{SMA}_{20} > \text{SMA}_{50} > \text{SMA}_{200}$.
- `moderately_bullish`: Price trading above $\text{SMA}_{50}$.
- `neutral`: Consolidating moving averages.
- `moderately_bearish`: Price trading below $\text{SMA}_{50}$.
- `bearish`: $P < \text{SMA}_{20} < \text{SMA}_{50} < \text{SMA}_{200}$.
- `golden_cross`: $\text{SMA}_{50}$ crosses above $\text{SMA}_{200}$.
- `death_cross`: $\text{SMA}_{50}$ crosses below $\text{SMA}_{200}$.

### 2. Momentum State
Combines RSI and MACD oscillator dynamics:
- `overbought`: $\text{RSI}_{14} \ge 70$.
- `bullish_momentum`: $\text{RSI}_{14} \ge 50$ with expanding positive MACD histogram.
- `neutral`: $\text{RSI}_{14}$ balanced between 40 and 60.
- `bearish_momentum`: $\text{RSI}_{14} < 50$ with negative MACD histogram.
- `oversold`: $\text{RSI}_{14} \le 30$.

### 3. Volatility Regime
Classifies annualized return dispersion:
- `low`: Annualized volatility $< 15\%$.
- `normal`: $15\% \le \sigma_{\text{ann}} \le 35\%$.
- `high`: $35\% < \sigma_{\text{ann}} \le 60\%$.
- `extreme`: $\sigma_{\text{ann}} > 60\%$.

### 4. Composite Technical Score (0 - 100)
A calibrated composite index synthesizing:
- Baseline: 50 (Neutral)
- Trend component ($\pm 25$)
- Momentum component ($\pm 20$)
- Volatility adjustment ($\pm 5$)
- Resulting verdict classifications: *Strong Bullish Uptrend* ($\ge 75$), *Moderate Bullish Bias* ($60-74$), *Neutral Consolidation* ($45-59$), *Moderate Bearish Bias* ($30-44$), *Strong Bearish Downtrend* ($< 30$), and *Oversold Reversal Watch* ($\text{RSI} \le 30$).
- Transparent rationales explaining every deduction or credit.

---

## 8. Next Steps in Phase 4

Following dependency order:
1. **Issue #38 (Complete):** Analytics domain and core price-based calculations.
2. **Issue #39 (Complete / Under Review in PR #44):** Technical indicators engine (SMA, EMA, RSI, MACD, Bollinger Bands).
3. **Issue #40 (Complete / Ready for PR):** Analytics service layer and market intelligence metrics (Trend, Momentum, Volatility Regime).
4. **Issue #41:** Analytics API endpoints and request/response schemas.
5. **Issue #42:** Product integration into frontend dashboards and interactive charts.
