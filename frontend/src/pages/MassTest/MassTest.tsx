/**
 * Mass Test — High-Throughput Bulk Inspection Engine UI.
 * Submits ZIP archives or multiple images to the shared persistent job queue,
 * monitors live job/batch progress, controls dispatch (pause/resume/cancel/retry),
 * and surfaces engine hardware/latency metrics.
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Upload, Play, Pause, XCircle, RotateCcw, Download, Cpu, Activity,
} from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listScannerUnits } from '../../services/scannerUnitService'
import {
  cancelBatch,
  getBatchResults,
  getBatchStatus,
  getEngineMetrics,
  getEngineStatus,
  listBatches,
  pauseBatch,
  resumeBatch,
  retryBatch,
  submitMassTest,
  type BatchResultItem,
  type BatchStatus,
  type EngineMetricsOut,
  type EngineStatusOut,
} from '../../services/massTestService'
import type { ScannerUnit } from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'

export default function MassTest() {
  const [scanners, setScanners] = useState<ScannerUnit[]>([])
  const [scannerId, setScannerId] = useState('')
  const [threshold, setThreshold] = useState(0.5)
  const [files, setFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [submitErr, setSubmitErr] = useState<string>()
  const [rejected, setRejected] = useState<Array<{ filename: string; reason: string }>>([])

  const [batches, setBatches] = useState<BatchStatus[]>([])
  const [activeBatchId, setActiveBatchId] = useState<string>()
  const [batchStatus, setBatchStatus] = useState<BatchStatus>()
  const [results, setResults] = useState<BatchResultItem[]>([])
  const [filterExec, setFilterExec] = useState('')
  const [filterDecision, setFilterDecision] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')

  const [engineStatus, setEngineStatus] = useState<EngineStatusOut>()
  const [engineMetrics, setEngineMetrics] = useState<EngineMetricsOut>()

  const refreshEngine = useCallback(async () => {
    try {
      const [st, mt, bs] = await Promise.all([
        getEngineStatus(),
        getEngineMetrics(),
        listBatches(15),
      ])
      setEngineStatus(st)
      setEngineMetrics(mt)
      setBatches(bs)
      if (!activeBatchId && bs.length > 0) {
        setActiveBatchId(bs[0].batch_id)
      }
    } catch {
      // keep existing state
    }
  }, [activeBatchId])

  const refreshActiveBatch = useCallback(async () => {
    if (!activeBatchId) return
    try {
      const [st, res] = await Promise.all([
        getBatchStatus(activeBatchId),
        getBatchResults(activeBatchId, {
          limit: 200,
          job_status: filterExec || undefined,
          decision: filterDecision || undefined,
          severity: filterSeverity || undefined,
        }),
      ])
      setBatchStatus(st)
      setResults(res.items)
    } catch {
      // ignore transient poll errors
    }
  }, [activeBatchId, filterExec, filterDecision, filterSeverity])

  useEffect(() => {
    listScannerUnits().then(setScanners).catch(() => {})
    void refreshEngine()
  }, [refreshEngine])

  useEffect(() => {
    void refreshActiveBatch()
    const timer = window.setInterval(() => {
      void refreshActiveBatch()
      void refreshEngine()
    }, 1500)
    return () => window.clearInterval(timer)
  }, [refreshActiveBatch, refreshEngine])

  const handleSubmit = async () => {
    if (!scannerId || files.length === 0) return
    setSubmitting(true)
    setSubmitErr(undefined)
    setRejected([])
    try {
      const resp = await submitMassTest(Number(scannerId), threshold, files)
      setRejected(resp.rejected_files ?? [])
      setActiveBatchId(resp.batch_id)
      setFiles([])
      await refreshEngine()
      await refreshActiveBatch()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSubmitErr(msg || 'Bulk submission failed.')
    } finally {
      setSubmitting(false)
    }
  }

  const exportCsv = () => {
    if (!results.length) return
    const headers = ['job_id', 'filename', 'execution_status', 'inspection_id', 'decision', 'quality_score', 'severity', 'latency_ms']
    const lines = [
      headers.join(','),
      ...results.map(r => [
        r.job_id,
        `"${r.original_filename.replace(/"/g, '""')}"`,
        r.execution_status,
        r.inspection_id ?? '',
        r.overall_decision ?? '',
        r.quality_score ?? '',
        r.severity ?? '',
        r.total_processing_ms ?? '',
      ].join(',')),
    ]
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${activeBatchId ?? 'mass_test'}_results.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-5">
      <div className="page-header flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1>Mass Test Engine</h1>
            <PageHelpLegend
              title="Mass Test Engine"
              summary="Submit ZIP archives or multiple images to the persistent inspection queue."
              items={[
                { label: 'Shared Pipeline', description: 'Mass Test and External API (/api/v1/jobs) use the same bounded CPU/GPU engine.' },
                { label: 'Execution Status', description: 'QUEUED → PREPROCESSING → PROCESSING → ANALYZING → COMPLETED / FAILED / CANCELLED.' },
                { label: 'Controls', description: 'Pause stops new dispatches safely; Cancel stops queued items; Retry requeues failures.' },
              ]}
            />
          </div>
          <p>High-throughput bulk inspection with persistent queuing, controlled GPU scheduling, and live telemetry.</p>
        </div>
      </div>

      {/* Engine Monitoring Strip */}
      {engineStatus && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-6">
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider flex items-center gap-1" style={{ color: 'var(--color-text-secondary)' }}>
              <Cpu size={12} /> Engine
            </div>
            <div className="mt-1 text-sm font-semibold">{engineStatus.engine_state} · {engineStatus.worker_state}</div>
          </div>
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>Queue Depth</div>
            <div className="mt-1 text-sm font-semibold tabular-nums">{engineStatus.queue_depth} queued / {engineStatus.active_jobs} active</div>
          </div>
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>Throughput</div>
            <div className="mt-1 text-sm font-semibold tabular-nums">{engineMetrics?.throughput_per_min ?? 0} img/min</div>
          </div>
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>P50 / P95 Latency</div>
            <div className="mt-1 text-sm font-semibold tabular-nums">
              {engineMetrics?.p50_latency_ms != null ? `${Math.round(engineMetrics.p50_latency_ms)} / ${Math.round(engineMetrics.p95_latency_ms ?? 0)} ms` : '—'}
            </div>
          </div>
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>RAM / CPU</div>
            <div className="mt-1 text-sm font-semibold tabular-nums">
              {engineStatus.ram_mb != null ? `${Math.round(engineStatus.ram_mb)} MB` : '—'} · {engineStatus.cpu_percent != null ? `${engineStatus.cpu_percent}%` : '—'}
            </div>
          </div>
          <div className="card p-3">
            <div className="text-[11px] uppercase tracking-wider flex items-center gap-1" style={{ color: 'var(--color-text-secondary)' }}>
              <Activity size={12} /> GPU / Models
            </div>
            <div className="mt-1 text-sm font-semibold tabular-nums">
              {engineStatus.gpu_available ? `CUDA (${Math.round(engineStatus.gpu_memory_mb ?? 0)} MB)` : 'CPU'} · {engineStatus.loaded_models.length} loaded
            </div>
          </div>
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        {/* Left: Submission + Batch Selector */}
        <section className="card p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium">Scanner Unit
              <select className={FIELD} value={scannerId} onChange={e => setScannerId(e.target.value)}>
                <option value="">Select a Scanner Unit...</option>
                {scanners.map(s => (
                  <option key={s.id} value={s.id}>{s.name} ({s.status})</option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium">
              Anomaly threshold: <span className="font-mono">{threshold.toFixed(2)}</span>
              <input
                type="range" min={0} max={1} step={0.05} value={threshold}
                onChange={e => setThreshold(+e.target.value)}
                className="mt-1 w-full accent-blue-600"
              />
            </label>
          </div>

          <label className="flex cursor-pointer flex-col items-center rounded-md border-2 border-dashed p-5 text-sm input-field hover:border-blue-400 transition-colors">
            <Upload size={22} />
            <span className="mt-1 font-medium text-center">
              {files.length > 0 ? `${files.length} file(s) selected` : 'Choose images or ZIP archive'}
            </span>
            <span className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
              ZIP, PNG, JPG, BMP, TIFF
            </span>
            <input
              type="file"
              multiple
              accept=".zip,image/*"
              className="sr-only"
              onChange={e => setFiles(Array.from(e.target.files ?? []))}
            />
          </label>

          <Button
            className="w-full justify-center"
            disabled={!scannerId || files.length === 0 || submitting}
            loading={submitting}
            onClick={handleSubmit}
          >
            <Play size={15} />
            {submitting ? 'Submitting Batch…' : 'Start Mass Test'}
          </Button>

          {submitErr && <ErrorState message={submitErr} />}

          {rejected.length > 0 && (
            <div className="rounded border border-amber-500/40 bg-amber-500/10 p-2.5 text-xs space-y-1">
              <div className="font-semibold text-amber-400">Rejected Files ({rejected.length})</div>
              {rejected.slice(0, 5).map((r, i) => (
                <div key={i} className="truncate">{r.filename}: {r.reason}</div>
              ))}
            </div>
          )}

          {batches.length > 0 && (
            <div className="border-t pt-3 space-y-1.5" style={{ borderColor: 'var(--color-border)' }}>
              <div className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                Recent Batches
              </div>
              <div className="space-y-1 max-h-56 overflow-y-auto">
                {batches.map(b => (
                  <button
                    key={b.batch_id}
                    onClick={() => setActiveBatchId(b.batch_id)}
                    className={`w-full text-left rounded border px-2.5 py-1.5 text-xs flex items-center justify-between ${
                      activeBatchId === b.batch_id ? 'border-blue-500 bg-blue-500/10' : ''
                    }`}
                    style={{ borderColor: activeBatchId === b.batch_id ? undefined : 'var(--color-border)' }}
                  >
                    <span className="font-mono font-medium">{b.batch_id}</span>
                    <span className="tabular-nums" style={{ color: 'var(--color-text-secondary)' }}>
                      {b.completed_items}/{b.total_items} ({b.status})
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Right: Live Progress + Controls + Results Table */}
        <section className="card p-4 space-y-4">
          {!batchStatus ? (
            <EmptyState
              title="No batch selected"
              body="Upload a ZIP archive or multiple images on the left to start a Mass Test batch."
            />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-base font-semibold font-mono">{batchStatus.batch_id}</h2>
                    <span className="rounded px-2 py-0.5 text-xs font-medium bg-blue-500/15 text-blue-400">
                      {batchStatus.status}
                    </span>
                  </div>
                  <p className="text-xs mt-0.5 tabular-nums" style={{ color: 'var(--color-text-secondary)' }}>
                    Elapsed: {batchStatus.elapsed_sec}s · Throughput: {batchStatus.throughput_per_min} img/min · Progress: {batchStatus.progress_pct}%
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  {batchStatus.is_paused ? (
                    <Button size="sm" variant="secondary" onClick={() => void resumeBatch(batchStatus.batch_id).then(setBatchStatus)}>
                      <Play size={13} /> Resume
                    </Button>
                  ) : (
                    <Button size="sm" variant="secondary" onClick={() => void pauseBatch(batchStatus.batch_id).then(setBatchStatus)}>
                      <Pause size={13} /> Pause
                    </Button>
                  )}
                  <Button size="sm" variant="secondary" onClick={() => void cancelBatch(batchStatus.batch_id).then(setBatchStatus)}>
                    <XCircle size={13} /> Cancel Pending
                  </Button>
                  {batchStatus.failed_items > 0 && (
                    <Button size="sm" variant="secondary" onClick={() => void retryBatch(batchStatus.batch_id).then(setBatchStatus)}>
                      <RotateCcw size={13} /> Retry Failed
                    </Button>
                  )}
                  <Button size="sm" variant="ghost" disabled={results.length === 0} onClick={exportCsv}>
                    <Download size={13} /> Export CSV
                  </Button>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="h-2 w-full rounded-full overflow-hidden bg-slate-700/30">
                <div
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${batchStatus.progress_pct}%` }}
                />
              </div>

              {/* 7 Execution Status Counts */}
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-2 text-center text-xs">
                {[
                  ['Total', batchStatus.total_items],
                  ['Queued', batchStatus.queued_items],
                  ['Prep', batchStatus.preprocessing_items],
                  ['Processing', batchStatus.processing_items],
                  ['Analyzing', batchStatus.analyzing_items],
                  ['Completed', batchStatus.completed_items],
                  ['Failed', batchStatus.failed_items],
                  ['Cancelled', batchStatus.cancelled_items],
                ].map(([lbl, val]) => (
                  <div key={String(lbl)} className="rounded border p-2 popup-subtle" style={{ borderColor: 'var(--color-border)' }}>
                    <div className="text-[11px]" style={{ color: 'var(--color-text-secondary)' }}>{lbl}</div>
                    <div className="text-sm font-semibold tabular-nums">{val}</div>
                  </div>
                ))}
              </div>

              {/* Filters */}
              <div className="flex flex-wrap gap-2">
                <select className="px-2.5 py-1.5 text-xs input-field" value={filterExec} onChange={e => setFilterExec(e.target.value)}>
                  <option value="">All Execution States</option>
                  {['QUEUED', 'PREPROCESSING', 'PROCESSING', 'ANALYZING', 'COMPLETED', 'FAILED', 'CANCELLED'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <select className="px-2.5 py-1.5 text-xs input-field" value={filterDecision} onChange={e => setFilterDecision(e.target.value)}>
                  <option value="">All Decisions</option>
                  <option value="PASS">PASS</option>
                  <option value="REVIEW_REQUIRED">REVIEW_REQUIRED</option>
                  <option value="FAIL">FAIL</option>
                </select>
                <select className="px-2.5 py-1.5 text-xs input-field" value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}>
                  <option value="">All Severities</option>
                  {['Critical', 'Major', 'Minor', 'Informational'].map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              {/* Results Table */}
              <div className="overflow-x-auto">
                <table>
                  <thead>
                    <tr>
                      <th>Job</th>
                      <th>File</th>
                      <th>Execution</th>
                      <th>Inspection</th>
                      <th>Decision</th>
                      <th>Severity</th>
                      <th className="tabular-nums">Score</th>
                      <th className="tabular-nums">Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.map(r => (
                      <tr key={r.job_id}>
                        <td className="font-mono text-xs">{r.job_id}</td>
                        <td className="max-w-[160px] truncate text-xs" title={r.original_filename}>{r.original_filename}</td>
                        <td className="text-xs font-medium">{r.execution_status}</td>
                        <td className="font-mono text-xs text-blue-500">
                          {r.inspection_id ? <Link to={`/inspections/${r.inspection_id}`}>{r.inspection_id}</Link> : '—'}
                        </td>
                        <td>
                          {r.overall_decision ? (
                            <StatusBadge value={r.overall_decision === 'PASS' ? 'Completed' : r.overall_decision === 'FAIL' ? 'Failed' : 'Needs review'} />
                          ) : '—'}
                        </td>
                        <td>{r.severity ? <StatusBadge value={r.severity} /> : '—'}</td>
                        <td className="tabular-nums">{r.quality_score ?? '—'}</td>
                        <td className="tabular-nums text-xs">
                          {r.total_processing_ms != null ? `${Math.round(r.total_processing_ms)} ms` : (r.error_message || '—')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
