import { apiClient } from './client'
import { ENDPOINTS } from './endpoints'

/**
 * CentFlow Portfolios and Holdings API Client
 */

/**
 * Fetch all portfolios with aggregate valuations.
 */
export async function listPortfolios() {
  return apiClient(ENDPOINTS.PORTFOLIOS)
}

/**
 * Fetch a specific portfolio with full holdings and position metrics.
 */
export async function getPortfolio(portfolioId) {
  return apiClient(ENDPOINTS.PORTFOLIO_DETAIL(portfolioId))
}

/**
 * Create a new investment portfolio.
 */
export async function createPortfolio({ name, description = '', baseCurrency = 'USD' }) {
  return apiClient(ENDPOINTS.PORTFOLIOS, {
    method: 'POST',
    body: JSON.stringify({
      name,
      description,
      base_currency: baseCurrency,
    }),
  })
}

/**
 * Add or accumulate a position in a portfolio.
 */
export async function addPosition(portfolioId, { symbol, quantity, averagePrice, currency = 'USD' }) {
  return apiClient(ENDPOINTS.PORTFOLIO_POSITIONS(portfolioId), {
    method: 'POST',
    body: JSON.stringify({
      symbol,
      quantity: Number(quantity),
      average_price: Number(averagePrice),
      currency,
    }),
  })
}

/**
 * Remove an existing position from a portfolio.
 */
export async function removePosition(portfolioId, positionId) {
  return apiClient(ENDPOINTS.PORTFOLIO_POSITION_DELETE(portfolioId, positionId), {
    method: 'DELETE',
  })
}
