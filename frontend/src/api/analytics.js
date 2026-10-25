import { apiClient } from './client'
import { ENDPOINTS } from './endpoints'

/**
 * CentFlow Analytics & Financial Intelligence API Client
 */

/**
 * Fetch high-level market intelligence summary (trend posture, momentum, score, rationales).
 *
 * @param {string} symbol - Asset ticker symbol.
 * @param {number} lookbackDays - Historical observation lookback window in days.
 * @param {string} interval - Bar frequency (e.g., '1d').
 * @returns {Promise<{data: Object}>} Response envelope containing market intelligence summary.
 */
export async function getAnalyticsSummary(symbol, lookbackDays = 365, interval = '1d') {
  return apiClient(ENDPOINTS.ANALYTICS_SUMMARY(symbol, lookbackDays, interval))
}

/**
 * Fetch timestamp-aligned technical indicator series (SMA, EMA, RSI, MACD, Bollinger Bands).
 *
 * @param {string} symbol - Asset ticker symbol.
 * @param {number} lookbackDays - Historical lookback window in days.
 * @param {string} interval - Bar frequency (e.g., '1d').
 * @param {Object} params - Indicator toggle options { includeRsi, includeMacd, includeBollinger }.
 * @returns {Promise<{data: Object}>} Response envelope containing indicator series.
 */
export async function getIndicatorSeries(symbol, lookbackDays = 365, interval = '1d', params = {}) {
  return apiClient(ENDPOINTS.ANALYTICS_INDICATORS(symbol, lookbackDays, interval, params))
}

/**
 * Fetch performance and risk distribution analysis (period return, volatility, max drawdown).
 *
 * @param {string} symbol - Asset ticker symbol.
 * @param {number} lookbackDays - Historical lookback window in days.
 * @param {string} interval - Bar frequency (e.g., '1d').
 * @param {number} annualizeFactor - Annualization scalar (252 for daily trading days).
 * @returns {Promise<{data: Object}>} Response envelope containing returns analysis.
 */
export async function getReturnsAnalysis(symbol, lookbackDays = 365, interval = '1d', annualizeFactor = 252) {
  return apiClient(ENDPOINTS.ANALYTICS_RETURNS(symbol, lookbackDays, interval, annualizeFactor))
}
