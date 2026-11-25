import { apiClient } from './api'
import type {
  CorrectionRecord,
  InspectionDetail,
  InspectionListItem,
  InspectionRunResult,
} from '../types'

export async function listInspections(params?: { limit?: number; offset?: number; status?: string }): Promise<InspectionListItem[]> {
  const { data } = await apiClient.get<InspectionListItem[]>('/inspections', { params })
  return data
}

export async function getInspection(id: string): Promise<InspectionDetail> {
  const { data } = await apiClient.get<InspectionDetail>(`/inspections/${id}`)
  return data
}

export async function getReviewQueue(limit = 50): Promise<InspectionListItem[]> {
  const { data } = await apiClient.get<InspectionListItem[]>('/inspections/review-queue', { params: { limit } })
  return data
}

export async function listCorrections(limit = 100): Promise<CorrectionRecord[]> {
  const { data } = await apiClient.get<CorrectionRecord[]>('/inspections/corrections', { params: { limit } })
  return data
}

export async function runInspection(
  req: {
    industry: string
    product: string
    pipelineId: string
    scannerUnitId?: number | null
    threshold: number
    fileName: string
  },
  file?: File,
): Promise<InspectionRunResult> {
  const form = new FormData()
  form.append('industry', req.industry)
  form.append('product', req.product)
  form.append('pipelineId', req.pipelineId)
  if (req.scannerUnitId != null) form.append('scannerUnitId', String(req.scannerUnitId))
  form.append('threshold', String(req.threshold))
  form.append('fileName', req.fileName)
  if (file) form.append('file', file)
  const { data } = await apiClient.post<InspectionRunResult>('/inspections', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function reviewInspection(
  id: string,
  decision: 'Approved' | 'Rejected',
  note: string,
  feedbackCategory = 'Correct detection',
): Promise<void> {
  await apiClient.post(`/inspections/${id}/review`, {
    decision,
    note,
    feedback_category: feedbackCategory,
  })
}

export async function confirmInspection(id: string): Promise<void> {
  await apiClient.post(`/inspections/${id}/confirm`, {})
}
