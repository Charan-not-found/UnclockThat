import { apiClient } from './api'
import type { TrainingJob } from '../types'

export interface StartTrainingReq {
  model_key?: string
  scanner_unit_id?: number | null
  module_id?: number | null
  dataset_id?: number | null
  strategy?: string
  max_epochs?: number
  limit_train_batches?: number
}

export interface StartBatchTrainingReq {
  scanner_unit_id: number
  dataset_id?: number | null
  mode: 'chained' | 'simultaneous'
  max_epochs?: number
  limit_train_batches?: number
}

export async function listTrainingJobs(): Promise<TrainingJob[]> {
  const { data } = await apiClient.get<TrainingJob[]>('/training-jobs')
  return data
}

export async function getTrainingJob(id: number): Promise<TrainingJob> {
  const { data } = await apiClient.get<TrainingJob>(`/training-jobs/${id}`)
  return data
}

export async function startTrainingJob(req: StartTrainingReq): Promise<TrainingJob> {
  const { data } = await apiClient.post<TrainingJob>('/training-jobs', req)
  return data
}

export async function startBatchTraining(req: StartBatchTrainingReq): Promise<TrainingJob[]> {
  const { data } = await apiClient.post<TrainingJob[]>('/training-jobs/batch', req)
  return data
}
