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
}
