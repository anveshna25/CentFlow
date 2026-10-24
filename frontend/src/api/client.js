/**
 * CentFlow Centralized API Client
 *
 * Normalizes HTTP requests and parses CentFlow API response envelopes
 * (ResponseEnvelope, PaginatedResponse, and ErrorResponse).
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

export async function apiClient(endpoint, options = {}) {
  const url = `${DEFAULT_BASE_URL}${endpoint}`
  const config = {
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
    ...options,
  }

  try {
    const response = await fetch(url, config)
    const contentType = response.headers.get('content-type')
    const isJson = contentType && contentType.includes('application/json')
    const data = isJson ? await response.json() : null

    if (!response.ok) {
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
