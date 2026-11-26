// Spec-correct type contracts for CLOCKIT frontend.

export type SpecStatus =
  | 'Completed'
  | 'Failed'
  | 'Needs review'
  | 'Needs dataset'
  | 'Training'
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
  | 'Validated'
  | 'Validation failed'
  | 'Uploaded'

export type SpecSeverity = 'Critical' | 'Major' | 'Minor' | 'Informational'

export interface Box { x: number; y: number; w: number; h: number }

export interface Defect {
  type: string
  severity: string
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
  heatmap_url?: string | null
  processing_time_ms?: number
}

export interface InspectionListItem {
  id: string
  date: string
  industry: string
  product: string
  station: string
  pipeline: string
  status: string
  quality_score: number
  severity: string
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
  image_url?: string | null
  model_used?: string | null
  module_results?: ModuleScanResult[]
  weighted_outputs?: WeightedOutput[]
  distinct_outputs?: InspectionRunResult['distinct_outputs']
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
  model_used?: string
  heatmap_url?: string | null
  module_results?: ModuleScanResult[]
  weighted_outputs?: WeightedOutput[]
  distinct_outputs?: {
    defect_classes?: string[]
    heatmaps?: Array<{ module_id: number; module_name: string; heatmap_url: string }>
    bounding_boxes_count?: number
    unique_module_outputs?: Array<{
      module_id: number
      module_name: string
      output_key: string
      summary: string
      shared: boolean
    }>
  }
  score: number
  isMock: boolean
}

export interface ModuleScanResult {
  module_id: number
  module_name: string
  model_key: string
  model_display_name: string
  weight: number
  weight_ratio: number
  selected_outputs: string[]
  anomaly_score: number
  confidence_score: number
  defects: Defect[]
  defect_classes: string[]
  heatmap_url?: string | null
  processing_time_ms?: number | null
}

export interface WeightedOutput {
  output_key: string
  label: string
  weighted_value: number
  weights_used: Array<{
    module_id: number
    module_name: string
    weight: number
    ratio: number
    value: number
  }>
}

export interface CorrectionRecord {
  id: number
  inspection_id: string
  feedback_category: string
  original_decision?: string
  corrected_decision: string
  note: string
  saved_image_path?: string
  review_status: string
  created_at: string
}

export interface ModelOutputSpec {
  key: string
  label: string
  description: string
}

export interface ModelCapability {
  model_key: string
  display_name: string
  model_family: string
  task: string
  integration_state: 'available_integrated' | 'downloaded_not_integrated' | 'planned_unavailable' | 'disabled_by_admin'
  is_enabled?: boolean
  training_paradigm: string
  requires_dataset: boolean
  dataset_requirements: string
  supported_training_strategies: string[]
  supported_outputs: ModelOutputSpec[]
  limitations: string
  pretrained_path?: string | null
  pretrained_present: boolean
  trained_checkpoint_path?: string | null
  ready_for_inference: boolean
}

export interface AnalysisModule {
  id: number
  scanner_unit_id: number
  name: string
  description?: string | null
  purpose?: string | null
  model_key: string
  model_display_name: string
  dataset_id?: number | null
  dataset_name?: string | null
  dataset_validation_status?: string | null
  selected_outputs: string[]
  weight?: number
  config?: Record<string, unknown> | null
  state: string
  created_at: string
  updated_at: string
}

export interface ScannerUnit {
  id: number
  name: string
  description?: string | null
  industry: string
  product_name?: string | null
  status: string
  module_count: number
  modules: AnalysisModule[]
  created_at: string
  updated_at: string
}

export interface DatasetRecord {
  id: number
  name: string
  category: string
  industry: string
  source_filename: string
  file_count: number
  valid_image_count: number
  invalid_file_count: number
  duplicate_count: number
  validation_status: string
  validation_details?: { errors?: string[] } | null
  sha256_hash?: string | null
  created_at: string
}

export interface TrainingJob {
  id: number
  scanner_unit_id?: number | null
  scanner_unit_name?: string | null
  module_id?: number | null
  module_name?: string | null
  dataset_id?: number | null
  model_key: string
  strategy: string
  status: string
  progress_pct: number
  current_step: string
  logs: string[]
  max_epochs: number
  limit_train_batches: number
  metrics?: Record<string, unknown> | null
  checkpoint_path?: string | null
  error_message?: string | null
  started_at?: string | null
  completed_at?: string | null
  created_at: string
}

export interface ModelInfo {
  id: string
  name: string
  task: string
  version: string
  state: string
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
  state: string
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
