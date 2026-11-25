/**
 * Centralized API client. Base URL from environment.
 * Never silently substitutes mock data on failure.
 */
import axios from 'axios'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: BASE,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// Error classification
export type ApiErrorCode =
  | 'NETWORK_UNAVAILABLE'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'VALIDATION_FAILED'
  | 'SERVER_ERROR'
  | 'UNKNOWN'

export interface ApiError {
  code: ApiErrorCode
  message: string
  detail?: string
}

export function classifyError(err: unknown): ApiError {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status
    if (!err.response) return { code: 'NETWORK_UNAVAILABLE', message: 'Cannot reach the CLOCKIT server. Is the backend running?' }
    if (status === 401) return { code: 'UNAUTHORIZED', message: 'Session expired or not authenticated.' }
    if (status === 403) return { code: 'FORBIDDEN', message: 'You do not have permission to perform this action.' }
    if (status === 404) return { code: 'NOT_FOUND', message: 'Resource not found.' }
    if (status === 422) return { code: 'VALIDATION_FAILED', message: 'Validation error.', detail: JSON.stringify(err.response.data) }
    if (status && status >= 500) return { code: 'SERVER_ERROR', message: 'Server error. Check backend logs.', detail: String(status) }
  }
  return { code: 'UNKNOWN', message: 'An unexpected error occurred.' }
}
