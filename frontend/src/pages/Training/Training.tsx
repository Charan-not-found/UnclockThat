/**
 * Training Center — launch EfficientAD-Small training jobs, detect training issues
 * (missing or empty ZIP dataset), and monitor progress in a Real-time tab.
 */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Dumbbell, Play, RefreshCw, AlertTriangle, Activity } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listTrainingJobs, startTrainingJob } from '../../services/trainingService'
import { listDatasets } from '../../services/datasetService'
import { listScannerUnits } from '../../services/scannerUnitService'
import { classifyError } from '../../services/api'
import type { DatasetRecord, ScannerUnit, TrainingJob } from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'

export default function Training() {
  const [searchParams] = useSearchParams()
  const [tab, setTab] = useState<'runs' | 'realtime'>('runs')
  const [jobs, setJobs] = useState<TrainingJob[]>()
  const [datasets, setDatasets] = useState<DatasetRecord[]>([])
  const [units, setUnits] = useState<ScannerUnit[]>([])
  const [err, setErr] = useState<string>()

  const [datasetId, setDatasetId] = useState<string>('')
  const [modelKey, setModelKey] = useState<string>(searchParams.get('modelKey') ?? 'patchcore')
  const [unitId, setUnitId] = useState<string>(searchParams.get('unitId') ?? '')
  const [moduleId, setModuleId] = useState<string>(searchParams.get('moduleId') ?? '')
  const [maxEpochs, setMaxEpochs] = useState(2)
  const [limitBatches, setLimitBatches] = useState(50)
  const [starting, setStarting] = useState(false)
  const [startErr, setStartErr] = useState('')

  const load = async () => {
    setErr(undefined)
    try {
      const [j, d, u] = await Promise.all([listTrainingJobs(), listDatasets(), listScannerUnits()])
      setJobs(j)
      setDatasets(d)
      setUnits(u)
    } catch (e) {
      setErr(classifyError(e).message)
    }
  }

  useEffect(() => { void load() }, [])

  // Poll every 2s while any job is Queued or Running
  useEffect(() => {
    const active = jobs?.some(j => j.status === 'Queued' || j.status === 'Running')
    if (!active) return
    const timer = setInterval(() => {
      listTrainingJobs().then(setJobs).catch(() => {})
    }, 2000)
    return () => clearInterval(timer)
  }, [jobs])

  // Detect training issues before allowing start
  const selectedDataset = datasets.find(d => String(d.id) === datasetId)
  let trainingIssue = ''
  if (datasets.length === 0) {
    trainingIssue = 'No dataset uploaded yet. Upload a non-empty .zip or image dataset in Datasets before training.'
  } else if (!datasetId) {
    trainingIssue = 'No dataset selected. Choose a validated dataset below to start training.'
  } else if (selectedDataset && (selectedDataset.validation_status !== 'Validated' || selectedDataset.valid_image_count <= 0)) {
    trainingIssue = `Selected dataset "${selectedDataset.name}" is empty (0 valid images) or failed validation. Upload a valid non-empty .zip.`
  }

  const handleStart = async () => {
    if (trainingIssue) {
      setStartErr(trainingIssue)
      return
    }
    setStarting(true)
    setStartErr('')
    try {
      await startTrainingJob({
        model_key: modelKey,
        dataset_id: Number(datasetId),
        scanner_unit_id: unitId ? Number(unitId) : null,
        module_id: moduleId ? Number(moduleId) : null,
        strategy: 'initial_training',
        max_epochs: maxEpochs,
        limit_train_batches: limitBatches,
      })
      await load()
      setTab('realtime')
    } catch (e) {
      setStartErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setStarting(false)
    }
  }

  if (!jobs && !err) return <LoadingState message="Loading training jobs…" />
  if (err) return <ErrorState message="Failed to load training center" detail={err} onRetry={load} />

  const hasRunning = jobs?.some(j => j.status === 'Queued' || j.status === 'Running')
  const latestJob = jobs?.[0]

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Training Center</h1>
            <PageHelpLegend
              title="Training Center"
              summary="Runs isolated EfficientAD training on GPU (CUDA) or CPU using your validated dataset."
              items={[
                { label: 'Queued', badge: 'Queued', description: 'Job is waiting to start (max 1 concurrent job).' },
                { label: 'Running', badge: 'Running', description: 'Training in progress; watch the Real-time Progress tab.' },
                { label: 'Completed', badge: 'Completed', description: 'Checkpoint saved and linked module marked Ready.' },
                { label: 'Failed', badge: 'Failed', description: 'Training stopped with an error; inspect the log.' },
              ]}
            />
          </div>
          <p>Launch EfficientAD-Small training runs, inspect dataset readiness, and monitor live progress.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {/* Start Training Job Form */}
      <section className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Dumbbell size={16} className="text-blue-500" />
          <h2 className="font-medium text-sm">Start EfficientAD-Small Training Run</h2>
        </div>

        {/* Training issues banner */}
        {(trainingIssue || startErr) && (
          <div className="flex items-start gap-2 rounded bg-amber-500/10 border border-amber-500/30 px-3 py-2.5 text-xs text-amber-500">
            <AlertTriangle size={15} className="mt-0.5 flex-shrink-0" />
            <div>
              <strong>Training Issue:</strong> {startErr || trainingIssue}{' '}
              {datasets.length === 0 && (
                <Link to="/datasets" className="underline font-medium ml-1">Go to Datasets →</Link>
              )}
            </div>
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-5">
          <label className="block text-xs font-medium">
            AI Model <span className="text-red-500">*</span>
            <select className={FIELD} value={modelKey} onChange={e => setModelKey(e.target.value)}>
              <option value="patchcore">PatchCore (WideResNet-50)</option>
              <option value="dinomaly">Dinomaly (DINOv2 ViT-B/14)</option>
              <option value="efficientad_medium">EfficientAD-Medium</option>
              <option value="efficientad_small">EfficientAD-Small</option>
            </select>
          </label>
          <label className="block text-xs font-medium">
            Training dataset <span className="text-red-500">*</span>
            <select className={FIELD} value={datasetId} onChange={e => { setDatasetId(e.target.value); setStartErr('') }}>
              <option value="">Select a validated dataset…</option>
              {datasets.map(d => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.valid_image_count} imgs · {d.validation_status})
                </option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium">
            Target Scanner Unit (optional)
            <select className={FIELD} value={unitId} onChange={e => { setUnitId(e.target.value); setModuleId('') }}>
              <option value="">None (global checkpoint)</option>
              {units.map(u => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-medium">
            Max epochs
            <input type="number" min={1} max={50} className={FIELD} value={maxEpochs} onChange={e => setMaxEpochs(Math.max(1, +e.target.value))} />
          </label>
          <label className="block text-xs font-medium">
            Batches per epoch
            <input type="number" min={5} max={2000} className={FIELD} value={limitBatches} onChange={e => setLimitBatches(Math.max(5, +e.target.value))} />
          </label>
        </div>

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Saves trained weights to <code>artifacts/trained/efficientad_casting.ckpt</code>.
          </p>
          <Button size="sm" loading={starting} disabled={!!hasRunning || !!trainingIssue} onClick={handleStart}>
            <Play size={14} /> {hasRunning ? 'Job Running…' : 'Start Training'}
          </Button>
        </div>
      </section>

      {/* Tabs: Training Runs | Real-time Progress */}
      <div className="flex gap-2 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <button
          onClick={() => setTab('runs')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'runs' ? 'border-blue-600 text-blue-500' : 'border-transparent opacity-70 hover:opacity-100'
          }`}
        >
          Training Runs ({jobs?.length ?? 0})
        </button>
        <button
          onClick={() => setTab('realtime')}
          className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'realtime' ? 'border-blue-600 text-blue-500' : 'border-transparent opacity-70 hover:opacity-100'
          }`}
        >
          <Activity size={14} className={hasRunning ? 'animate-pulse text-blue-500' : ''} />
          Real-time Progress
        </button>
      </div>

      {tab === 'realtime' ? (
        <section className="card p-5 space-y-4">
          {!latestJob ? (
            <EmptyState title="No active or recent training runs" body="Start a training run above to watch live progress and logs." />
          ) : (
            <>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="font-semibold">RUN-{latestJob.id} · {latestJob.model_key}</h2>
                    <StatusBadge value={latestJob.status} size="md" />
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                    Current stage: <strong>{latestJob.current_step}</strong>
                  </p>
                </div>
                <span className="text-2xl font-semibold tabular-nums">{latestJob.progress_pct}%</span>
              </div>

              {/* Real progress bar driven by backend events */}
              <div className="h-2.5 w-full rounded-full overflow-hidden popup-subtle border" style={{ borderColor: 'var(--color-border)' }}>
                <div
                  className={`h-full transition-all duration-500 ${
                    latestJob.status === 'Failed' ? 'bg-red-600' :
                    latestJob.status === 'Completed' ? 'bg-green-600' : 'bg-blue-600'
                  }`}
                  style={{ width: `${latestJob.progress_pct}%` }}
                />
              </div>

              {latestJob.error_message && (
                <div className="rounded bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-500">
                  {latestJob.error_message}
                </div>
              )}

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                  Live Execution Log
                </h3>
                <div className="rounded-md bg-slate-950 text-slate-200 p-3 font-mono text-xs max-h-64 overflow-y-auto space-y-1">
                  {latestJob.logs.length === 0 ? (
                    <span className="text-slate-500">Waiting for logs…</span>
                  ) : (
                    latestJob.logs.map((line, i) => <div key={i}>{line}</div>)
                  )}
                </div>
              </div>
            </>
          )}
        </section>
      ) : (
        <section className="card">
          {jobs && jobs.length === 0 ? (
            <EmptyState title="No training runs yet" body="Start a training run above to train EfficientAD-Small on your dataset." />
          ) : (
            <div className="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th>Run ID</th><th>Model</th><th>Progress</th><th>Step</th>
                    <th>Status</th><th>Metrics</th><th>Checkpoint</th><th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs?.map(j => (
                    <tr key={j.id}>
                      <td className="font-mono text-xs">RUN-{j.id}</td>
                      <td className="font-medium">{j.model_key}</td>
                      <td className="tabular-nums font-mono text-xs">{j.progress_pct}%</td>
                      <td className="text-xs">{j.current_step}</td>
                      <td>
                        <StatusBadge value={j.status} />
                        {j.error_message && <p className="text-xs text-red-500 mt-1 max-w-xs">{j.error_message}</p>}
                      </td>
                      <td className="text-xs font-mono">
                        {j.metrics ? Object.entries(j.metrics).map(([k, v]) => `${k}: ${v}`).join(', ') : '—'}
                      </td>
                      <td className="text-xs font-mono" style={{ color: 'var(--color-text-secondary)' }}>{j.checkpoint_path ?? '—'}</td>
                      <td className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{j.started_at ? new Date(j.started_at).toLocaleString() : 'Queued'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
