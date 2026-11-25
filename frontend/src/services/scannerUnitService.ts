import { apiClient } from './api'
import type { AnalysisModule, ModelCapability, ScannerUnit } from '../types'

export interface ScannerUnitCreateReq {
  name: string
  description?: string
  industry?: string
  product_name?: string
}

export interface ModulePayload {
  name: string
  description?: string
  purpose?: string
  model_key: string
  dataset_id?: number | null
  selected_outputs: string[]
}

export async function getModelCatalogue(): Promise<ModelCapability[]> {
  const { data } = await apiClient.get<ModelCapability[]>('/model-catalogue')
  return data
}

export async function listScannerUnits(): Promise<ScannerUnit[]> {
  const { data } = await apiClient.get<ScannerUnit[]>('/scanner-units')
  return data
}

export async function getScannerUnit(id: number): Promise<ScannerUnit> {
  const { data } = await apiClient.get<ScannerUnit>(`/scanner-units/${id}`)
  return data
}

export async function createScannerUnit(req: ScannerUnitCreateReq): Promise<ScannerUnit> {
  const { data } = await apiClient.post<ScannerUnit>('/scanner-units', req)
  return data
}

export async function updateScannerUnit(id: number, req: Partial<ScannerUnitCreateReq>): Promise<ScannerUnit> {
  const { data } = await apiClient.patch<ScannerUnit>(`/scanner-units/${id}`, req)
  return data
}

export async function deleteScannerUnit(id: number): Promise<void> {
  await apiClient.delete(`/scanner-units/${id}`)
}

export async function addModule(unitId: number, payload: ModulePayload): Promise<AnalysisModule> {
  const { data } = await apiClient.post<AnalysisModule>(`/scanner-units/${unitId}/modules`, payload)
  return data
}

export async function updateModule(unitId: number, moduleId: number, payload: ModulePayload): Promise<AnalysisModule> {
  const { data } = await apiClient.patch<AnalysisModule>(`/scanner-units/${unitId}/modules/${moduleId}`, payload)
  return data
}

export async function deleteModule(unitId: number, moduleId: number): Promise<void> {
  await apiClient.delete(`/scanner-units/${unitId}/modules/${moduleId}`)
}
