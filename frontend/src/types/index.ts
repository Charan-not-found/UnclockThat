// Spec-correct type contracts for CLOCKIT frontend.
// Status vocabulary: Completed / Failed / Needs review / Running / Queued / Draft / Configured / Ready / Disabled / Approved / Rejected / Archived
// Severity vocabulary: Informational / Minor / Major / Critical  (NOT low/medium/high)

export type SpecStatus =
  | 'Completed'
  | 'Failed'
  | 'Needs review'
  | 'Running'
  | 'Queued'
  | 'Draft'
  | 'Configured'
  | 'Ready'
  | 'Disabled'
  | 'Approved'
  | 'Rejected'
  | 'Archived'
  | 'Unavailable'

export type SpecSeverity = 'Critical' | 'Major' | 'Minor' | 'Informational'

// Legacy compat (used in older components, migrate gradually)
export type Status = 'pass' | 'fail' | 'review' | SpecStatus
export type Severity = 'low' | 'medium' | 'high' | 'none' | SpecSeverity

export interface Box { x: number; y: number; w: number; h: number }

export interface Defect {
  type: string
  severity: string   // SpecSeverity
  confidence: number
  anomalyScore: number
  box: Box
}

export interface AnomalyResult {
  id: string
  model_name: string
  anomaly_score: number
  confidence_score: number
  is_anomalous: boolean
  severity: string
  defects: Defect[]
  heatmap_path?: string
  processing_time_ms?: number
}

export interface InspectionListItem {
  id: string
  date: string
  industry: string
  product: string
  station: string
  pipeline: string
  status: string        // SpecStatus
  quality_score: number
  severity: string      // SpecSeverity
  defect_count: number
  requires_review: boolean
}

export interface InspectionDetail {
  id: string
  date: string
  industry: string
  product: string
  station: string
  pipeline: string
  pipeline_id?: string
  status: string
  overall_decision: string
  quality_score: number
  severity: string
  image_path: string
  requires_review: boolean
  review_note?: string
  anomaly_results: AnomalyResult[]
}

export interface InspectionRunResult {
  inspectionId: string
  quality_score: number
  status: string
  overall_decision: string
  severity: string
  defects: Defect[]
  score: number         // alias for quality_score
  isMock: boolean
}

export interface ModelInfo {
  id: string
  name: string
  task: string
  version: string
  state: string         // SpecStatus
  enabled: boolean
  model_family: string
  weights_path: string
  dataset_path: string
  has_weights_file: boolean
}

export interface Pipeline {
  id: string
  name: string
  version: string
  description?: string
  manufacturer: string
  is_active: boolean
  state: string         // SpecStatus
  stages: PipelineStage[]
  thresholds?: Record<string, number>
  created_at: string
}

export interface PipelineStage {
  id: string
  type: string
  label?: string
  model_id?: string
  note?: string
  params?: Record<string, unknown>
}

export interface AnalyticsSummary {
  total_inspections: number
  pass_count: number
  fail_count: number
  review_count: number
  pass_rate_pct: number | null
  anomaly_rate_pct: number | null
  date_range_days: number
  note: string
}

export interface DailyPoint {
  day: string
  inspections: number
  anomalies: number
  reviews: number
}

export interface SeverityCount {
  severity: string
  count: number
}

export interface StatusCount {
  status: string
  count: number
}

// Legacy compat — kept for components not yet migrated
export interface Inspection extends InspectionListItem {
  score: number
  defects: number
}
export interface InspectionResult {
  inspectionId?: string
  score: number
  status: string
  defects: Defect[]
  isMock?: boolean
}
export interface InspectionRequest {
  industry: string
  product: string
  pipelineId: string
  threshold: number
  fileName: string
}
