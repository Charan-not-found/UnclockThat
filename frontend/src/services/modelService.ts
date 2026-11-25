import { delay, USE_MOCK, api } from './api'
import { models } from './mockData'
import type { ModelInfo } from '../types'

export async function listModels(): Promise<ModelInfo[]> {
  if (!USE_MOCK) return (await api.get('/models')).data
  await delay(300)
  return models
}

export async function toggleModel(id: string): Promise<ModelInfo> {
  if (USE_MOCK) {
    const found = models.find(m => m.id === id)
    if (!found) throw new Error('Model not found')
    return { ...found, enabled: !found.enabled }
  }
  return (await api.patch(`/models/${encodeURIComponent(id)}/toggle`)).data
}
