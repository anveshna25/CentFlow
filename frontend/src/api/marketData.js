import { apiClient } from './client'
import { ENDPOINTS } from './endpoints'

/**
 * Fetch application system health status.
 */
export async function getSystemHealth() {
  return apiClient(ENDPOINTS.HEALTH)
}

/**
 * Fetch active market data provider connectivity status.
 */
export async function getProviderStatus() {
  return apiClient(ENDPOINTS.MARKET_DATA_STATUS)
}

/**
 * Fetch latest normalized quote for an instrument symbol.
 */
export async function getQuote(symbol) {
  return apiClient(ENDPOINTS.MARKET_DATA_QUOTE(symbol))
}

/**
 * Fetch batch of normalized quotes for multiple instrument symbols in a single request.
 */
export async function getQuotes(symbols) {
  return apiClient(ENDPOINTS.MARKET_DATA_QUOTES(symbols))
}

/**
 * Fetch historical OHLCV bars for an instrument symbol.
 */
export async function getHistoricalBars(symbol, days = 30, interval = '1d') {
  return apiClient(ENDPOINTS.MARKET_DATA_HISTORY(symbol, days, interval))
}

/**
 * Search or filter available instruments by keyword and optional asset category.
 */
export async function searchInstruments(query = '', assetType = '') {
  return apiClient(ENDPOINTS.MARKET_DATA_INSTRUMENTS(query, assetType))
}

/**
 * Ingest live quote observation into persistent database.
 */
export async function ingestQuote(symbol) {
  return apiClient(ENDPOINTS.MARKET_DATA_INGEST_QUOTE(symbol), { method: 'POST' })
}

/**
 * Trigger historical backfill for an instrument.
 */
export async function backfillHistoricalBars(symbol, days = 30, interval = '1d') {
  return apiClient(ENDPOINTS.MARKET_DATA_BACKFILL(symbol), {
    method: 'POST',
    body: JSON.stringify({ days, interval }),
  })
}

/**
 * Fetch persisted historical price observations from database.
 */
export async function getPersistedHistory(symbol, days = 30, interval = '1d') {
  return apiClient(ENDPOINTS.MARKET_DATA_PERSISTED_HISTORY(symbol, days, interval))
}
