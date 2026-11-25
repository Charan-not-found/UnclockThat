import { apiClient } from './api'
import type { AnalyticsSummary, DailyPoint, SeverityCount, StatusCount } from '../types'

export async function getSummary(days = 30): Promise<AnalyticsSummary> {
  const { data } = await apiClient.get<AnalyticsSummary>('/analytics/summary', { params: { days } })
  return data
}

export async function getTrend(days = 7): Promise<DailyPoint[]> {
  const { data } = await apiClient.get<DailyPoint[]>('/analytics/trend', { params: { days } })
  return data
}

export async function getSeverityDistribution(days = 30): Promise<SeverityCount[]> {
  const { data } = await apiClient.get<SeverityCount[]>('/analytics/severity-distribution', { params: { days } })
  return data
}

export async function getStatusDistribution(days = 30): Promise<StatusCount[]> {
  const { data } = await apiClient.get<StatusCount[]>('/analytics/status-distribution', { params: { days } })
  return data
}
