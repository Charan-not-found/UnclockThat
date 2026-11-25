import { apiClient } from './api'
import type { DatasetRecord } from '../types'

export async function listDatasets(): Promise<DatasetRecord[]> {
  const { data } = await apiClient.get<DatasetRecord[]>('/datasets')
  return data
}

export async function uploadDataset(
  params: { name: string; category: string; industry: string },
  files: File[],
): Promise<DatasetRecord> {
  const form = new FormData()
  form.append('name', params.name)
  form.append('category', params.category)
  form.append('industry', params.industry)
  for (const f of files) {
    form.append('files', f)
  }
  const { data } = await apiClient.post<DatasetRecord>('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  })
  return data
}

export async function validateDataset(id: number): Promise<DatasetRecord> {
  const { data } = await apiClient.post<DatasetRecord>(`/datasets/${id}/validate`, {})
  return data
}

export async function deleteDataset(id: number): Promise<void> {
  await apiClient.delete(`/datasets/${id}`)
}
