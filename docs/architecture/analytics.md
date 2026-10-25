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
├── __init__.py           # Public exports for domain contracts and calculations
├── domain.py             # Analytical value objects, metrics, and observation windows
├── calculations.py       # Core deterministic price, return, volatility, and drawdown formulas
└── indicators.py         # (Phase 4 subsequent step) Technical indicators (SMA, EMA, RSI, MACD, etc.)
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

## 5. Next Steps in Phase 4

Following dependency order:
1. **Issue #38 (Current):** Analytics domain and core price-based calculations.
2. **Issue #39:** Technical indicators engine (SMA, EMA, RSI, MACD, Bollinger Bands).
3. **Issue #40:** Analytics service layer and market intelligence metrics (Trend, Momentum, Volatility Regime).
4. **Issue #41:** Analytics API endpoints and request/response schemas.
5. **Issue #42:** Product integration into frontend dashboards and interactive charts.
