import { api, delay, USE_MOCK } from './api'
import { inspections } from './mockData'
import type { Inspection, InspectionRequest, InspectionResult } from '../types'

export async function listInspections(): Promise<Inspection[]> {
  if (!USE_MOCK) return (await api.get('/inspections')).data
  await delay(400)
  return inspections
}

export async function runInspection(req: InspectionRequest, file?: File): Promise<InspectionResult> {
  if (!USE_MOCK) {
    const form = new FormData()
    form.append('industry', req.industry)
    form.append('product', req.product)
    form.append('pipelineId', req.pipelineId)
    form.append('threshold', String(req.threshold))
    form.append('fileName', req.fileName)
    if (file) form.append('file', file)
    return (await api.post('/inspections', form)).data
  }
  await delay(2500)
  return {
    isMock: true,
    score: 64,
    status: 'review',
    defects: [
      { type: 'Scratch', severity: 'medium', confidence: 0.91, anomalyScore: 0.78, box: { x: 22, y: 30, w: 24, h: 18 } },
      { type: 'Contamination', severity: 'low', confidence: 0.74, anomalyScore: 0.52, box: { x: 58, y: 55, w: 18, h: 20 } },
    ],
  }
}

export async function confirmInspection(inspectionId: string): Promise<void> {
  if (USE_MOCK) return
  await api.post(`/inspections/${encodeURIComponent(inspectionId)}/confirm`)
}
