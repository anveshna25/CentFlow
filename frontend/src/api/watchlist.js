import { apiClient } from './client'
import { ENDPOINTS } from './endpoints'

/**
 * CentFlow Watchlist API service.
 * Handles persistent watchlist management, items tracking, and quote enrichment.
 */

export async function getWatchlists(userId = null) {
  const url = userId ? `${ENDPOINTS.WATCHLISTS}?user_id=${encodeURIComponent(userId)}` : ENDPOINTS.WATCHLISTS
  const res = await apiClient(url)
  return res.data || []
}

export async function getDefaultWatchlist() {
  const res = await apiClient(ENDPOINTS.WATCHLIST_DEFAULT)
  return res.data
}

export async function getWatchlist(watchlistId) {
  const res = await apiClient(ENDPOINTS.WATCHLIST_DETAIL(watchlistId))
  return res.data
}

export async function createWatchlist({ name, description = null }) {
  const res = await apiClient(ENDPOINTS.WATCHLISTS, {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })
  return res.data
}

export async function deleteWatchlist(watchlistId) {
  const res = await apiClient(ENDPOINTS.WATCHLIST_DETAIL(watchlistId), {
    method: 'DELETE',
  })
  return res.data
}

export async function addToWatchlist(watchlistId, symbol) {
  const res = await apiClient(ENDPOINTS.WATCHLIST_ITEMS(watchlistId), {
    method: 'POST',
    body: JSON.stringify({ symbol: symbol.trim().toUpperCase() }),
  })
  return {
    item: res.data,
    wasCreated: res.meta?.was_created ?? true,
  }
}

export async function removeFromWatchlist(watchlistId, symbolOrId) {
  const res = await apiClient(ENDPOINTS.WATCHLIST_ITEM(watchlistId, symbolOrId), {
    method: 'DELETE',
  })
  return res.data
}
