export type Status = 'pass' | 'fail' | 'review'
export type Severity = 'low' | 'medium' | 'high'
export interface Defect { type: string; severity: Severity; confidence: number; anomalyScore: number; box: { x: number; y: number; w: number; h: number } }
export interface Inspection { id: string; date: string; industry: string; product: string; pipeline: string; status: Status; score: number; severity: Severity | 'none'; defects: number }
export interface Pipeline { id: string; name: string; industry: string }
export interface ModelInfo { id: string; name: string; task: string; version: string; enabled: boolean; accuracy: number }
export interface InspectionResult { inspectionId?: string; score: number; status: Status; defects: Defect[]; isMock?: boolean }
export interface InspectionRequest { industry: string; product: string; pipelineId: string; threshold: number; fileName: string }
