/**
 * CentFlow API Endpoint Constants
 */

export const ENDPOINTS = {
  HEALTH: '/health',
  API_V1_HEALTH: '/api/v1/health',
  MARKET_DATA_STATUS: '/api/v1/market-data/status',
  MARKET_DATA_QUOTE: (symbol) => `/api/v1/market-data/quotes/${encodeURIComponent(symbol)}`,
  MARKET_DATA_HISTORY: (symbol, days = 30, interval = '1d') =>
    `/api/v1/market-data/history/${encodeURIComponent(symbol)}?days=${days}&interval=${interval}`,
  MARKET_DATA_INSTRUMENTS: (query = '') =>
    query
      ? `/api/v1/market-data/instruments?q=${encodeURIComponent(query)}`
      : '/api/v1/market-data/instruments',
  MARKET_DATA_INGEST_QUOTE: (symbol) =>
    `/api/v1/market-data/ingest/quote/${encodeURIComponent(symbol)}`,
  MARKET_DATA_BACKFILL: (symbol) =>
    `/api/v1/market-data/ingest/backfill/${encodeURIComponent(symbol)}`,
  MARKET_DATA_PERSISTED_HISTORY: (symbol, days = 30, interval = '1d') =>
    `/api/v1/market-data/persisted-history/${encodeURIComponent(symbol)}?days=${days}&interval=${interval}`,
  ASSETS: '/api/v1/assets',
  WATCHLISTS: '/api/v1/watchlists',
  PORTFOLIOS: '/api/v1/portfolios',
  PORTFOLIO_DETAIL: (portfolioId) => `/api/v1/portfolios/${encodeURIComponent(portfolioId)}`,
  PORTFOLIO_POSITIONS: (portfolioId) => `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/positions`,
  PORTFOLIO_POSITION_DELETE: (portfolioId, positionId) =>
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/positions/${encodeURIComponent(positionId)}`,
  ANALYTICS_SUMMARY: (symbol, lookbackDays = 365, interval = '1d') =>
    `/api/v1/analytics/summary/${encodeURIComponent(symbol)}?lookback_days=${lookbackDays}&interval=${interval}`,
  ANALYTICS_INDICATORS: (symbol, lookbackDays = 365, interval = '1d', params = {}) => {
    const query = new URLSearchParams({ lookback_days: String(lookbackDays), interval })
    if (params.includeRsi !== undefined) query.set('include_rsi', String(params.includeRsi))
    if (params.includeMacd !== undefined) query.set('include_macd', String(params.includeMacd))
    if (params.includeBollinger !== undefined) query.set('include_bollinger', String(params.includeBollinger))
    return `/api/v1/analytics/indicators/${encodeURIComponent(symbol)}?${query.toString()}`
  },
  ANALYTICS_RETURNS: (symbol, lookbackDays = 365, interval = '1d', annualizeFactor = 252) =>
    `/api/v1/analytics/returns/${encodeURIComponent(symbol)}?lookback_days=${lookbackDays}&interval=${interval}&annualize_factor=${annualizeFactor}`,
}
