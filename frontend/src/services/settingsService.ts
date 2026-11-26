import { apiClient } from './api'

export interface ModelToggleSetting {
  model_key: string
  display_name: string
  model_family: string
  task: string
  is_enabled: boolean
  ready_for_inference: boolean
}

export async function listModelToggles(): Promise<ModelToggleSetting[]> {
  const { data } = await apiClient.get<ModelToggleSetting[]>('/settings/models')
  return data
}

export async function toggleModelSetting(modelKey: string): Promise<ModelToggleSetting> {
  const { data } = await apiClient.patch<ModelToggleSetting>(`/settings/models/${modelKey}/toggle`, {})
  return data
}
