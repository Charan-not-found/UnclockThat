import { apiClient } from './api'
import type { ModelInfo } from '../types'

export async function listModels(): Promise<ModelInfo[]> {
  const { data } = await apiClient.get<ModelInfo[]>('/models')
  return data
}

export async function getModel(id: string): Promise<ModelInfo> {
  const { data } = await apiClient.get<ModelInfo>(`/models/${id}`)
  return data
}

export async function toggleModel(id: string): Promise<ModelInfo> {
  const { data } = await apiClient.patch<ModelInfo>(`/models/${id}/toggle`)
  return data
}
