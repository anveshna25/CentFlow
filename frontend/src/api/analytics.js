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
 * Fetch performance, risk-adjusted returns, and comparative benchmark analysis.
 *
 * @param {string} symbol - Asset ticker symbol.
 * @param {number} lookbackDays - Historical lookback window in days.
 * @param {string} interval - Bar frequency (e.g., '1d').
 * @param {number} annualizeFactor - Annualization scalar (252 for daily trading days).
 * @param {string|null} benchmark - Benchmark ticker symbol (e.g., 'SPY').
 * @param {number} riskFreeRate - Annual risk-free rate scalar (e.g., 0.04 for 4%).
 * @returns {Promise<{data: Object}>} Response envelope containing returns and benchmark analysis.
 */
export async function getReturnsAnalysis(symbol, lookbackDays = 365, interval = '1d', annualizeFactor = 252, benchmark = null, riskFreeRate = 0.0) {
  return apiClient(ENDPOINTS.ANALYTICS_RETURNS(symbol, lookbackDays, interval, annualizeFactor, benchmark, riskFreeRate))
}
