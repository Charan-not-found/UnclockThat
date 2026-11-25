import { apiClient } from './api'
import type { Pipeline } from '../types'

export interface PipelineCreateReq {
  name: string
  description?: string
  manufacturer_name?: string
  industry?: string
  stages?: Array<{ id: string; type: string; label?: string; note?: string }>
  thresholds?: Record<string, number>
}

export async function listPipelines(): Promise<Pipeline[]> {
  const { data } = await apiClient.get<Pipeline[]>('/pipelines')
  return data
}

export async function getPipeline(id: string): Promise<Pipeline> {
  const { data } = await apiClient.get<Pipeline>(`/pipelines/${id}`)
  return data
}

export async function createPipeline(req: PipelineCreateReq): Promise<Pipeline> {
  const { data } = await apiClient.post<Pipeline>('/pipelines', req)
  return data
}

export async function togglePipeline(id: string): Promise<Pipeline> {
  const { data } = await apiClient.patch<Pipeline>(`/pipelines/${id}/toggle`)
  return data
}
