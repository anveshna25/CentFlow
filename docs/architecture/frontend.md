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
    └── state/                  # State & navigation context
        ├── pages.js            # Canonical page route constants
        └── NavigationContext.jsx # SPA navigation provider & useNavigation hook
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
- **Responsive Layout:** Automatically adapts to container dimensions via `ResizeObserver`.

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
   - High-level KPIs: S&P 500 (SPY), Bitcoin (BTC-USD), Microsoft (MSFT), and active provider status.
   - Active Market Watch table with real-time price indications and 24h delta percentages.
2. **Markets & Instruments (`MarketsPage.jsx`):**
   - Interactive filtering by asset category (`all`, `equity`, `crypto`, `etf`).
   - Debounced live text search filtering across symbols, company names, and exchanges.
   - Formatted market table with volumes, prices, and badges.
   - **Interactive Modal Inspection:** Clicking any instrument opens a full-screen drawer modal featuring the live `PriceChart`, key statistics (Open, 24h High/Low, Previous Close, Volume), and action triggers to persist quotes or backfill 30-day historical bars.
3. **Watchlists (`WatchlistsPage.jsx`):**
   - User-defined instrument groupings (Mega-Cap Tech, Decentralized L1s, Macro Hedges).
   - Tracked symbol chips and collective daily momentum.
4. **Portfolios (`PortfoliosPage.jsx`):**
   - Valuation metrics: Total Valuation, Unrealized P&L, Cash Reserves.
   - Positions table: Instrument, Quantity, Average Entry Price, Current Price, Market Value, and P&L.
