# CentFlow Frontend Architecture & Application Shell

## 1. Overview & Philosophy

The CentFlow frontend application provides a fast, responsive, and visually refined market intelligence interface. It translates conceptual domain entities (Assets, Instruments, Markets, Watchlists, Portfolios, and Price feeds) into actionable views, interactive charts, and dashboards.

### Core Architectural Principles

1. **Modular Layer Separation:** Visual layout, atomic UI components, view containers, API clients, and navigation state are cleanly isolated.
2. **Vanilla CSS Design System:** Uses standard CSS variables and tokens for maximum performance, predictability, and flexibility, avoiding heavy utility CSS runtime dependencies.
3. **Decoupled API Boundary:** All backend communication routes through a centralized HTTP client (`apiClient`) configured to consume CentFlow's normalized API response envelopes (`ResponseEnvelope[T]`, `PaginatedResponse[T]`, and `ErrorResponse`).
4. **Zero-Dependency Navigation:** Employs a lightweight React Context navigation system synchronized with browser history and hash routing, keeping bundle size lean.
5. **Interactive Financial Visualization:** Custom SVG-based financial charting engine supporting line and candlestick representations, dynamic timeframes, volume histograms, and interactive hover crosshairs.
6. **Aesthetic Polish & Dark Mode:** Designed around a rich, deep-slate palette with glassmorphism surface elevation, financial delta colors (emerald green / coral red), and typography pairing Inter with Outfit.

---

## 2. Directory Structure

```text
frontend/
├── index.html                  # HTML entrypoint with font preloading & metadata
├── vite.config.js              # Vite bundler configuration
├── package.json                # React 19 dependencies & development scripts
│
└── src/
    ├── main.jsx                # React root mount entrypoint
    ├── App.jsx                 # Top-level application shell & view coordinator
    ├── App.css                 # Layout and responsive breakpoint styling
    ├── index.css               # Core design tokens, theme variables, reset
    │
    ├── api/                    # API client layer
    │   ├── client.js           # Centralized fetch wrapper & envelope parser
    │   ├── endpoints.js        # API route constants
    │   └── marketData.js       # Market data & ingestion query functions
    │
    ├── components/             # Reusable UI components
    │   ├── common/             # Atomic UI elements
    │   │   ├── Badge.jsx       # Status, trend, and category pills
    │   │   ├── Card.jsx        # Glassmorphic container with header & actions
    │   │   ├── LoadingSpinner.jsx # Smooth async state loader
    │   │   └── ErrorBanner.jsx # Standardized error envelope viewer
    │   ├── layout/             # Structural frame components
    │   │   ├── Header.jsx      # Top navigation, global search, status badge
    │   │   └── Sidebar.jsx     # Side navigation with route indicators
    │   └── market/             # Domain-specific components
    │       ├── StatWidget.jsx  # Metric KPI display card
    │       └── PriceChart.jsx  # Interactive Line & Candlestick financial chart
    │
    ├── layouts/                # Master layout shells
    │   └── AppLayout.jsx       # Coordinates sidebar, topbar, and main content
    │
    ├── pages/                  # Page-level route views
    │   ├── DashboardPage.jsx   # Market overview, benchmarks, quick watch
    │   ├── MarketsPage.jsx     # Instrument table, modal chart & debounced search
    │   ├── WatchlistsPage.jsx  # Watchlist curation & asset monitoring cards
    │   └── PortfoliosPage.jsx  # Portfolio holdings, valuations & return metrics
    │
    ├── state/                  # State & navigation context
    │   ├── pages.js            # Canonical page route constants
    │   └── NavigationContext.jsx # SPA navigation provider & useNavigation hook
    │
    └── utils/                  # Cross-cutting UI utilities
        └── highlight.jsx       # Substring match highlighting for financial search
```

---

## 3. Design System & Tokens (`index.css`)

The application design system is configured via CSS custom properties in [`frontend/src/index.css`](../../frontend/src/index.css):

| Token Category | Examples | Description |
| :--- | :--- | :--- |
| **Backgrounds** | `--cf-bg-base` (`#0a0e17`), `--cf-bg-surface` (`#111827`) | Deep dark slate foundations |
| **Glass Surfaces** | `--cf-bg-surface-glass` (`rgba(17, 24, 39, 0.75)`) | Translucent frosted glass effect (`blur(12px)`) |
| **Borders** | `--cf-border` (`rgba(255, 255, 255, 0.08)`) | Subtle boundary contrast |
| **Brand Accents** | `--cf-brand-primary` (`#3b82f6`), `--cf-brand-cyan` (`#06b6d4`) | Vibrant electric blue & cyan accents |
| **Financial Signals** | `--cf-bullish` (`#10b981`), `--cf-bearish` (`#ef4444`) | Emerald green gains, coral red declines |
| **Typography** | `--cf-font-sans` (`Inter`), `--cf-font-display` (`Outfit`) | Clean body text and modern display headings |

---

## 4. Interactive Financial Charting (`PriceChart.jsx`)

The [`PriceChart`](../../frontend/src/components/market/PriceChart.jsx) provides high-performance SVG financial visualization without external heavy charting bundles:

### 4.1 Capabilities
- **Dual View Modes:**
  - **Line:** Smooth path with gradient area fill fading into the dark background.
  - **Candlestick:** Real-time green/red candle bodies with high/low wick lines.
- **Dynamic Timeframes:** Support for `1D`, `1W`, `1M`, `1Y`, and `ALL` intervals with automated scale recalculation.
- **Volume Histogram:** Lower 18% histogram reflecting trading volume with bullish/bearish tinting.
- **Hover Crosshairs & Glassmorphism Tooltip:** Interactive crosshair tracking the closest observation, displaying exact open, high, low, close, volume, and date.
- **Technical Indicator Overlays:**
  - **SMA 20 & SMA 50:** Moving average trend curves (amber and magenta).
  - **EMA 12:** Exponential moving average short-term trend curve (cyan).
  - **Bollinger Bands:** Upper and lower volatility envelope (dashed indigo) with translucent corridor fill and middle moving average line.
- **Oscillator Sub-Chart Panels:**
  - **RSI (14):** Dedicated oscillator sub-panel with 70 overbought and 30 oversold reference levels, 50 centerline, and lavender oscillator line.
  - **MACD (12, 26, 9):** Dedicated sub-panel with zero centerline, positive/negative histogram bars, MACD line (cyan), and Signal line (orange).
- **Synchronized Multi-Panel Crosshairs:** When scrubbing across the chart, the crosshair slices through primary price, volume bars, RSI, and MACD panels simultaneously, displaying active values in the tooltip.
- **Responsive Layout:** Automatically adapts to container dimensions via `ResizeObserver`.

### 4.2 Market Intelligence Card (`MarketIntelligenceCard.jsx`)

The [`MarketIntelligenceCard`](../../frontend/src/components/market/MarketIntelligenceCard.jsx) renders high-level quantitative intelligence synthesized by CentFlow's analytics engine:
- **Composite Technical Score Gauge (0–100):** Visual score display with dynamic color-coding (Strong Bullish, Bullish, Neutral, Cautious, Bearish).
- **Trend Posture Badge:** Primary directional bias (Bullish / Bearish / Neutral) with alignment arrow icons.
- **Momentum State:** Oscillator impulse state derived from RSI and MACD.
- **Volatility Regime:** Bandwidth and return volatility rating (Low, Normal, High, Extreme).
- **Synthesis Verdict Callout:** Plain-English summary headline explaining the current technical setup.
- **Factor Drivers & Rationales:** List of deterministic bullet explanations detailing the exact conditions driving the evaluation.
- **Risk & Performance Distribution:** Historical period returns, annualized volatility, max drawdown, and recovery status.

### 4.3 Central Asset Detail Experience (`AssetDetailModal.jsx`)

The [`AssetDetailModal`](../../frontend/src/components/market/AssetDetailModal.jsx) acts as the central asset hub for inspecting individual instruments:
- **Asset Identity Header:** Symbol, full asset name, exchange tag, asset classification badge, and settlement currency.
- **Headline Pricing & 24h Visual Range Bar:** Large formatted real-time price, absolute and percentage change indicators, and an interactive 24h high/low gradient slider with an active price indicator.
- **Key Statistics Matrix:** Open, High, Low, Previous Close, Volume, Market Classification, and Trading Status.
- **Cross-Platform Actions:** Direct triggers for "+ Watchlist" (quick add feedback), "+ Position in Portfolio" (auto-navigates to portfolio view), "Persist Quote Observation", and "Backfill 30-Day History".
- **Multi-Tab Exploration Modes:**
  - `Comprehensive`: Synchronized display of both the `PriceChart` and `MarketIntelligenceCard`.
  - `Technical Chart`: Dedicated technical chart with timeframe selector (`1D`, `1W`, `1M`, `1Y`, `ALL`) and technical indicator overlays.
  - `Market Intelligence & Signals`: Factor scores, risk distribution, and deterministic drivers.
  - `Instrument Profile & Provenance`: Exchange settlement rules, data provider provenance (`MOCK` / `YAHOO`), and cache architecture.
- **Accessibility & Interaction:** Closes on backdrop click or `Escape` key, and automatically syncs when opened via URL hash parameters.

### 4.4 Quantitative Analytics Integration Components

- **[`TechnicalPostureBadge`](../../frontend/src/components/analytics/TechnicalPostureBadge.jsx):** Normalized, accessible visual indicator mapping backend `TrendPosture`, `MomentumState`, and composite factor scores to standardized color tokens (`bullish`, `bearish`, `warning`, `brand`, `neutral`) with direction icons and optional score display.
- **[`MarketRegimeDistribution`](../../frontend/src/components/analytics/MarketRegimeDistribution.jsx):** Multi-asset quantitative market consensus component rendering:
  - Multi-segment trend posture distribution track (Bullish vs. Neutral vs. Bearish percentages).
  - Consensus factor score meter (0–100) and regime classification.
  - Volatility regime dispersion counts (Normal, Low, High, Extreme).

### 4.5 Global Asset Search & Discovery (`Header.jsx`, `highlight.jsx`)

CentFlow provides a unified, cross-platform asset search and discovery engine:
- **Instant Debounced Search:** Asynchronously queries `GET /api/v1/market-data/instruments?q=...` with a 250ms debounce threshold and local fallback cache support.
- **Autocomplete Results Dropdown:**
  - Dynamic result counter and navigation tips.
  - Formatted instrument rows featuring bold ticker symbols, entity names, asset type badges (`EQUITY`, `CRYPTO`, `ETF`), and listing venues (`NASDAQ`, `Coinbase`, `NYSE`).
  - Substring search highlighting via [`highlightMatch`](../../frontend/src/utils/highlight.jsx).
- **Pro-Trader Keyboard Navigation:** Full `ArrowUp` / `ArrowDown` selection cycling, `Enter` to inspect highlighted asset, and `Escape` to dismiss.
- **Global Hotkey:** `Ctrl+K` (or `⌘+K` / `/`) immediately focuses the global search bar from anywhere across the product.
- **Universal Asset Inspection:** Selecting an instrument from the search dropdown smoothly opens the comprehensive [`AssetDetailModal`](../../frontend/src/components/market/AssetDetailModal.jsx) as an overlay from any page without losing navigation state.
- **Catalog Search & Empty States:** The [`MarketsPage`](../../frontend/src/pages/MarketsPage.jsx) directory features synchronized external search, category pills (`all`, `equity`, `crypto`, `etf`), substring highlighting, and informative empty search states with one-click filter reset.

---

## 5. Navigation & State Management

Navigation is managed via [`NavigationContext`](../../frontend/src/state/NavigationContext.jsx):

```jsx
import { useNavigation } from './state/NavigationContext'
import { PAGES } from './state/pages'

function NavigationTrigger() {
  const { activePage, navigate } = useNavigation()

  return (
    <button onClick={() => navigate(PAGES.MARKETS)}>
      Go to Markets
    </button>
  )
}
```

- Synchronizes automatically with `window.location.hash` (`#dashboard`, `#markets`, `#watchlists`, `#portfolios`).
- Allows bookmarking and browser back/forward navigation without requiring full page reloads or heavy external routing packages.

---

## 6. Page Views & Capabilities

1. **Dashboard (`DashboardPage.jsx`):**
   - **Live Index Benchmarks:** Real-time KPI widgets for S&P 500 (SPY), Nasdaq 100 (QQQ), Bitcoin (BTC-USD), and Ethereum (ETH-USD) enriched with real-time `TechnicalPostureBadge` pills and click-to-explore navigation.
   - **Market Breadth & Environment Bar:** Advancing vs. Declining asset count, average benchmark drift, provider connectivity health, and manual refresh controls.
   - **Cross-Asset Market Regimes Distribution:** Comprehensive quantitative consensus overview showing market-wide trend distribution, average factor score, and volatility regime dispersion.
   - **Macro Regime Highlights:** Quantitative factor postures, consensus scores, and narrative rationales for core equity (SPY) and crypto (BTC-USD) benchmarks.
   - **Active Benchmark Instruments Table:** Filterable by category (`all`, `equity`, `crypto`, `etf`) with live quotes, volume metrics, technical posture pills, and direct "Inspect & Chart" deep-links.
2. **Markets & Instruments (`MarketsPage.jsx`):**
   - Interactive filtering by asset category (`all`, `equity`, `crypto`, `etf`).
   - Debounced live text search filtering across symbols, company names, and exchanges.
   - Formatted market table with volumes, prices, and badges.
   - **Central Asset Detail Experience:** Clicking any instrument opens the dedicated [`AssetDetailModal`](../../frontend/src/components/market/AssetDetailModal.jsx) featuring:
     - Header, pricing headline with `TechnicalPostureBadge`, factor posture strip, and 24h High/Low range slider bar.
     - Key financial statistics grid (Open, High, Low, Previous Close, Volume, Classification).
     - **View Mode Navigation Tabs:** Toggle between `Comprehensive (Chart & Intelligence)`, `Technical Chart & Overlays`, `Market Intelligence & Factor Signals`, and `Instrument Profile & Provenance`.
     - Direct platform action buttons: "+ Watchlist", "+ Position in Portfolio", "Persist Quote Observation", and "Backfill 30-Day History".
3. **Watchlists (`WatchlistsPage.jsx`):**
   - Multi-collection watchlist switcher (Mega-Cap Tech, Decentralized L1s, Macro Hedges, and custom user-created baskets).
   - Real-time aggregate performance KPIs: Average Daily Drift, Technical Consensus % Bullish, and Consensus Factor Score.
   - **Interactive Watchlist Table:** Live quotes, 24h changes, compact `TechnicalPostureBadge` pills, momentum classifications, volatility regimes, and direct modal inspection triggers.
   - Seamless custom watchlist creation modal with comma/space symbol parsing.
4. **Portfolios (`PortfoliosPage.jsx`):**
   - **Real-Time Marked-to-Market Valuation:** Dynamic valuation KPIs (Total Value, Unrealized P&L $ and %, Invested Cost Basis, Active Positions count) calculated against live provider quotes.
   - **Aggregate Risk & Volatility Exposure:** Portfolio-weighted factor health score, capital-weighted trend posture distribution track (% Bullish, % Neutral, % Bearish), asset allocation breakdown (Equity, Crypto, ETF), and volatility dispersion profile.
   - **Open Holdings Table:** Interactive table tracking each holding's asset category, quantity, entry price, current price, market value, unrealized return, and `TechnicalPostureBadge` posture pill.
   - **Holding Inspection:** Direct "Inspect" trigger opening [`AssetDetailModal`](../../frontend/src/components/market/AssetDetailModal.jsx) without leaving the portfolio screen.
   - **Position Lifecycle Management:** Modal forms for adding/accumulating holdings and closing positions.
   - **Multi-Portfolio Support:** Create and toggle across multiple dedicated portfolios.
