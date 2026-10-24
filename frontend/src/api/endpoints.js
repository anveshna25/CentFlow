/**
 * CentFlow API Endpoint Constants
 */

export const ENDPOINTS = {
  HEALTH: '/health',
  API_V1_HEALTH: '/api/v1/health',
  ASSETS: '/api/v1/assets',
  INSTRUMENTS: '/api/v1/instruments',
  MARKET_DATA_QUOTE: (symbol) => `/api/v1/market-data/quotes/${encodeURIComponent(symbol)}`,
  MARKET_DATA_HISTORY: (symbol) => `/api/v1/market-data/history/${encodeURIComponent(symbol)}`,
  WATCHLISTS: '/api/v1/watchlists',
  PORTFOLIOS: '/api/v1/portfolios',
}
