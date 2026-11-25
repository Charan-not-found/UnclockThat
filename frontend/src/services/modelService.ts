import { delay, USE_MOCK, api } from './api'
import { models } from './mockData'
import type { ModelInfo } from '../types'
export async function listModels(): Promise<ModelInfo[]> { if (!USE_MOCK) return (await api.get('/models')).data; await delay(300); return models }
