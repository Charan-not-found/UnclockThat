import { apiClient } from './api'

interface SeedResult {
  created_manufacturer: boolean
  created_models: string[]
  created_pipeline: boolean
  message: string
}

export async function seedDatabase(): Promise<SeedResult> {
  const { data } = await apiClient.post<SeedResult>('/admin/seed', {})
  return data
}
