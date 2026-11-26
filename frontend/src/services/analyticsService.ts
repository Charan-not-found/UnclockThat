import { apiClient } from './api'
import type { AnalyticsSummary, DailyPoint, SeverityCount, StatusCount } from '../types'

export interface ScannerUnitStats {
  scanner_unit_id: number | null
  scanner_unit_name: string
  total_inspections: number
  pass_count: number
  fail_count: number
  review_count: number
  pass_rate_pct: number | null
  anomaly_rate_pct: number | null
}

export async function getSummary(days = 30, scannerUnitId?: number): Promise<AnalyticsSummary> {
  const { data } = await apiClient.get<AnalyticsSummary>('/analytics/summary', {
    params: { days, ...(scannerUnitId != null ? { scanner_unit_id: scannerUnitId } : {}) },
  })
  return data
}

export async function getTrend(days = 7, scannerUnitId?: number): Promise<DailyPoint[]> {
  const { data } = await apiClient.get<DailyPoint[]>('/analytics/trend', {
    params: { days, ...(scannerUnitId != null ? { scanner_unit_id: scannerUnitId } : {}) },
  })
  return data
}

export async function getSeverityDistribution(days = 30, scannerUnitId?: number): Promise<SeverityCount[]> {
  const { data } = await apiClient.get<SeverityCount[]>('/analytics/severity-distribution', {
    params: { days, ...(scannerUnitId != null ? { scanner_unit_id: scannerUnitId } : {}) },
  })
  return data
}

export async function getStatusDistribution(days = 30, scannerUnitId?: number): Promise<StatusCount[]> {
  const { data } = await apiClient.get<StatusCount[]>('/analytics/status-distribution', {
    params: { days, ...(scannerUnitId != null ? { scanner_unit_id: scannerUnitId } : {}) },
  })
  return data
}

export async function getAnalyticsByScannerUnit(days = 30): Promise<ScannerUnitStats[]> {
  const { data } = await apiClient.get<ScannerUnitStats[]>('/analytics/by-scanner-unit', {
    params: { days },
  })
  return data
}
