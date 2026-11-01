/**
 * CentFlow Centralized API Client
 *
 * Normalizes HTTP requests, handles session cookies and CSRF headers,
 * and parses CentFlow API response envelopes (ResponseEnvelope, PaginatedResponse, and ErrorResponse).
 */

export class ApiError extends Error {
  constructor(message, code = 'API_ERROR', status = 500, details = []) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

const DEFAULT_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

let onUnauthorizedCallback = null

/**
 * Register global listener for 401 Unauthorized API responses.
 * Used by AuthContext to transition to unauthenticated state.
 */
export function setUnauthorizedHandler(callback) {
  onUnauthorizedCallback = callback
}

/**
 * Helper to read non-HttpOnly cookies from document.cookie (e.g. centflow_csrf).
 */
export function getCookie(name) {
  if (typeof document === 'undefined') return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return null
}

export async function apiClient(endpoint, options = {}) {
  const url = `${DEFAULT_BASE_URL}${endpoint}`
  const method = (options.method || 'GET').toUpperCase()

  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...options.headers,
  }

  // Double-submit CSRF cookie protection on mutating HTTP requests
  if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
    const csrfToken = getCookie('centflow_csrf')
    if (csrfToken && !headers['X-CSRF-Token']) {
      headers['X-CSRF-Token'] = csrfToken
    }
  }

  const config = {
    credentials: 'include', // Automatically send HttpOnly session cookies
    ...options,
    headers,
  }

  try {
    const response = await fetch(url, config)
    const contentType = response.headers.get('content-type')
    const isJson = contentType && contentType.includes('application/json')
    const data = isJson ? await response.json() : null

    if (!response.ok) {
      if (response.status === 401 && onUnauthorizedCallback) {
        onUnauthorizedCallback()
      }

      const errorPayload = data?.error || {}
      throw new ApiError(
        errorPayload.message || response.statusText || 'Request failed',
        errorPayload.code || `HTTP_${response.status}`,
        response.status,
        errorPayload.details || []
      )
    }

    // CentFlow standard envelope parsing
    if (data && 'data' in data) {
      return {
        data: data.data,
        meta: data.meta || null,
        pagination: data.pagination || null,
      }
    }

    return data
  } catch (err) {
    if (err instanceof ApiError) {
      throw err
    }
    throw new ApiError(
      err.message || 'Network error encountered.',
      'NETWORK_ERROR',
      0
    )
  }
}
