import { apiClient } from './api'

export interface BatchSubmitResponse {
  batch_id: string
  status: string
  total_items: number
  completed_items: number
  rejected_files: Array<{ filename: string; reason: string }>
  status_url: string
}

export interface BatchStatus {
  batch_id: string
  source_type: string
  scanner_unit_id: number
  status: string
  is_paused: boolean
  total_items: number
  queued_items: number
  preprocessing_items: number
  processing_items: number
  analyzing_items: number
  completed_items: number
  failed_items: number
  cancelled_items: number
  progress_pct: number
  elapsed_sec: number
  throughput_per_min: number
  created_at: string
  started_at?: string | null
  completed_at?: string | null
}

export interface BatchResultItem {
  job_id: string
  original_filename: string
  execution_status: string
  inspection_id?: string | null
  overall_decision?: string | null
  quality_score?: number | null
  severity?: string | null
  total_processing_ms?: number | null
  error_code?: string | null
  error_message?: string | null
}

export interface BatchResultsPage {
  batch_id: string
  total: number
  limit: number
  offset: number
  items: BatchResultItem[]
}

export interface EngineStatusOut {
  engine_state: string
  worker_state: string
  worker_threads: number
  queue_depth: number
  active_jobs: number
  loaded_models: Array<{
    instance_key: string
    model_key: string
    device: string
    state: string
    load_time_ms: number
    use_count: number
    error_message?: string | null
  }>
  gpu_available: boolean
  cpu_percent?: number | null
  ram_mb?: number | null
  gpu_memory_mb?: number | null
}

export interface EngineMetricsOut {
  window: string
  queue_depth: number
  total_accepted_jobs: number
  completed_jobs: number
  failed_jobs: number
  failure_rate_pct: number
  throughput_per_min: number
  avg_queue_wait_ms?: number | null
  avg_processing_latency_ms?: number | null
  p50_latency_ms?: number | null
  p95_latency_ms?: number | null
  avg_model_load_ms: number
  cpu_percent?: number | null
  ram_mb?: number | null
  gpu_memory_mb?: number | null
}

export async function submitMassTest(
  scannerUnitId: number,
  threshold: number,
  files: File[],
): Promise<BatchSubmitResponse> {
  const form = new FormData()
  form.append('scanner_unit_id', String(scannerUnitId))
  form.append('source_type', 'MASS_TEST')
  form.append('threshold', String(threshold))
  for (const f of files) {
    form.append('files', f)
  }
  const { data } = await apiClient.post<BatchSubmitResponse>('/jobs/bulk', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function listBatches(limit = 20): Promise<BatchStatus[]> {
  const { data } = await apiClient.get<BatchStatus[]>('/batches', { params: { limit } })
  return data
}

export async function getBatchStatus(batchId: string): Promise<BatchStatus> {
  const { data } = await apiClient.get<BatchStatus>(`/batches/${batchId}`)
  return data
}

export async function getBatchResults(
  batchId: string,
  params?: { limit?: number; offset?: number; job_status?: string; decision?: string; severity?: string },
): Promise<BatchResultsPage> {
  const { data } = await apiClient.get<BatchResultsPage>(`/batches/${batchId}/results`, { params })
  return data
}

export async function pauseBatch(batchId: string): Promise<BatchStatus> {
  const { data } = await apiClient.post<BatchStatus>(`/batches/${batchId}/pause`, {})
  return data
}

export async function resumeBatch(batchId: string): Promise<BatchStatus> {
  const { data } = await apiClient.post<BatchStatus>(`/batches/${batchId}/resume`, {})
  return data
}

export async function cancelBatch(batchId: string): Promise<BatchStatus> {
  const { data } = await apiClient.post<BatchStatus>(`/batches/${batchId}/cancel`, {})
  return data
}

export async function retryBatch(batchId: string): Promise<BatchStatus> {
  const { data } = await apiClient.post<BatchStatus>(`/batches/${batchId}/retry`, {})
  return data
}

export async function getEngineStatus(): Promise<EngineStatusOut> {
  const { data } = await apiClient.get<EngineStatusOut>('/engine/status')
  return data
}

export async function getEngineMetrics(): Promise<EngineMetricsOut> {
  const { data } = await apiClient.get<EngineMetricsOut>('/engine/metrics')
  return data
}
