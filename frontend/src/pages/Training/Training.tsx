/**
 * Training Center — select a Scanner Unit and train a single module or ALL modules
 * (chained one-by-one or simultaneous), with Real-time Progress monitoring.
 */
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Dumbbell, Play, RefreshCw, AlertTriangle, Activity, Layers } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listTrainingJobs, startTrainingJob, startBatchTraining } from '../../services/trainingService'
import { listDatasets } from '../../services/datasetService'
import { listScannerUnits, getModelCatalogue } from '../../services/scannerUnitService'
import { classifyError } from '../../services/api'
import type { DatasetRecord, ModelCapability, ScannerUnit, TrainingJob } from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'
const TRAINABLE_KEYS = new Set(['patchcore', 'dinomaly', 'omniposead', 'anomalydino', 'efficientad_medium', 'efficientad_small'])

export default function Training() {
  const [searchParams] = useSearchParams()
  const [tab, setTab] = useState<'runs' | 'realtime'>('runs')
  const [jobs, setJobs] = useState<TrainingJob[]>()
  const [datasets, setDatasets] = useState<DatasetRecord[]>([])
  const [units, setUnits] = useState<ScannerUnit[]>([])
  const [catalogue, setCatalogue] = useState<ModelCapability[]>([])
  const [err, setErr] = useState<string>()

  const [unitId, setUnitId] = useState<string>(searchParams.get('unitId') ?? '')
  const [moduleId, setModuleId] = useState<string>(searchParams.get('moduleId') ?? '')
  const [batchMode, setBatchMode] = useState<'chained' | 'simultaneous'>('chained')
  const [modelKey, setModelKey] = useState<string>(searchParams.get('modelKey') ?? 'patchcore')
  const [datasetId, setDatasetId] = useState<string>('')
  const [maxEpochs, setMaxEpochs] = useState(2)
  const [limitBatches, setLimitBatches] = useState(50)
  const [starting, setStarting] = useState(false)
  const [startErr, setStartErr] = useState('')

  const applyModuleConfig = (unit: ScannerUnit | undefined, modIdStr: string) => {
    if (!unit) return
    if (modIdStr === 'ALL') {
      setModuleId('ALL')
      const firstWithDs = unit.modules.find(m => TRAINABLE_KEYS.has(m.model_key) && m.dataset_id)
      setDatasetId(firstWithDs?.dataset_id ? String(firstWithDs.dataset_id) : '')
      return
    }
    const trainableMods = unit.modules.filter(m => TRAINABLE_KEYS.has(m.model_key))
    const mod = unit.modules.find(m => String(m.id) === modIdStr) ?? trainableMods[0] ?? unit.modules[0]
    if (mod) {
      setModuleId(String(mod.id))
      if (TRAINABLE_KEYS.has(mod.model_key)) setModelKey(mod.model_key)
      setDatasetId(mod.dataset_id ? String(mod.dataset_id) : '')
    } else {
      setModuleId('')
    }
  }

  const load = async () => {
    setErr(undefined)
    try {
      const [j, d, u, c] = await Promise.all([
        listTrainingJobs(),
        listDatasets(),
        listScannerUnits(),
        getModelCatalogue(),
      ])
      setJobs(j)
      setDatasets(d)
      setUnits(u)
      setCatalogue(c)

      const initialUnitId = searchParams.get('unitId') ?? unitId
      const initialModId = searchParams.get('moduleId') ?? moduleId
      if (initialUnitId) {
        const found = u.find(x => String(x.id) === initialUnitId)
        applyModuleConfig(found, initialModId)
      }
    } catch (e) {
      setErr(classifyError(e).message)
    }
  }

  useEffect(() => { void load() }, [])

  useEffect(() => {
    const active = jobs?.some(j => j.status === 'Queued' || j.status === 'Running')
    if (!active) return
    const timer = setInterval(() => {
      listTrainingJobs().then(setJobs).catch(() => {})
    }, 2000)
    return () => clearInterval(timer)
  }, [jobs])

  const handleUnitChange = (newUnitId: string) => {
    setUnitId(newUnitId)
    setStartErr('')
    const found = units.find(x => String(x.id) === newUnitId)
    if (found) {
      applyModuleConfig(found, '')
    } else {
      setModuleId('')
    }
  }

  const handleModuleChange = (newModId: string) => {
    setModuleId(newModId)
    setStartErr('')
    const found = units.find(x => String(x.id) === unitId)
    applyModuleConfig(found, newModId)
  }

  const selectedUnit = units.find(u => String(u.id) === unitId)
  const isAllModules = Boolean(selectedUnit && moduleId === 'ALL')
  const selectedModule = !isAllModules ? selectedUnit?.modules.find(m => String(m.id) === moduleId) : undefined
  const selectedCap = catalogue.find(c => c.model_key === modelKey)
  const selectedDataset = datasets.find(d => String(d.id) === datasetId)
  const unitTrainableMods = selectedUnit?.modules.filter(m => TRAINABLE_KEYS.has(m.model_key)) ?? []

  let trainingIssue = ''
  if (isAllModules) {
    if (unitTrainableMods.length === 0) {
      trainingIssue = `Scanner Unit "${selectedUnit?.name}" has no trainable modules.`
    } else {
      const missingDs = unitTrainableMods.find(m => !m.dataset_id && !datasetId)
      if (missingDs) {
        trainingIssue = `Module "${missingDs.name}" has no dataset assigned. Choose a fallback dataset below or assign one in Scanner Units.`
      }
    }
  } else if (selectedCap && selectedCap.is_enabled === false) {
    trainingIssue = `Model "${selectedCap.display_name}" is disabled in Settings. Enable it in Settings before training.`
  } else if (selectedUnit && selectedUnit.modules.length === 0) {
    trainingIssue = `Scanner Unit "${selectedUnit.name}" has no Analysis Modules yet. Add one in Scanner Units first.`
  } else if (selectedModule && !TRAINABLE_KEYS.has(selectedModule.model_key)) {
    trainingIssue = `Module "${selectedModule.name}" uses ${selectedModule.model_display_name}, which does not use this normal-only training runner.`
  } else if (datasets.length === 0) {
    trainingIssue = 'No dataset uploaded yet. Upload a non-empty .zip or image dataset in Datasets before training.'
  } else if (!datasetId) {
    trainingIssue = selectedModule
      ? `Module "${selectedModule.name}" has no dataset assigned. Select a validated dataset below or assign one in Scanner Units.`
      : 'No dataset selected. Choose a validated dataset below to start training.'
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
      if (isAllModules && selectedUnit) {
        await startBatchTraining({
          scanner_unit_id: selectedUnit.id,
          dataset_id: datasetId ? Number(datasetId) : null,
          mode: batchMode,
          max_epochs: maxEpochs,
          limit_train_batches: limitBatches,
        })
      } else {
        await startTrainingJob({
          model_key: modelKey,
          dataset_id: Number(datasetId),
          scanner_unit_id: unitId ? Number(unitId) : null,
          module_id: moduleId ? Number(moduleId) : null,
          strategy: 'initial_training',
          max_epochs: maxEpochs,
          limit_train_batches: limitBatches,
        })
      }
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
  const activeOrLatestJobs = jobs?.filter(j => j.status === 'Queued' || j.status === 'Running') ?? []
  const realtimeJobs = activeOrLatestJobs.length > 0 ? activeOrLatestJobs : (jobs?.slice(0, 1) ?? [])
  const trainableModels = catalogue.filter(c => TRAINABLE_KEYS.has(c.model_key))

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Training Center</h1>
            <PageHelpLegend
              title="Training Center"
              summary="Train a single module or ALL trainable modules of a Scanner Unit (chained one-by-one or simultaneously)."
              items={[
                { label: 'Chained', description: 'Trains modules sequentially one-by-one (recommended for 6 GB GPU VRAM).' },
                { label: 'Simultaneous', description: 'Trains all selected modules in parallel threads.' },
                { label: 'Running', badge: 'Running', description: 'Training in progress; watch the Real-time Progress tab.' },
                { label: 'Completed', badge: 'Completed', description: 'Cloned module checkpoint saved and module marked Ready.' },
              ]}
            />
          </div>
          <p>Select a Scanner Unit to train one or all modules according to its configuration.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      <section className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Dumbbell size={16} className="text-blue-500" />
          <h2 className="font-medium text-sm">Configure & Start Training Run</h2>
        </div>

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
            Scanner Unit
            <select className={FIELD} value={unitId} onChange={e => handleUnitChange(e.target.value)}>
              <option value="">Manual (no Scanner Unit)</option>
              {units.map(u => (
                <option key={u.id} value={u.id}>{u.name} ({u.module_count} modules)</option>
              ))}
            </select>
          </label>

          {selectedUnit ? (
            <label className="block text-xs font-medium">
              Analysis Module
              <select className={FIELD} value={moduleId} onChange={e => handleModuleChange(e.target.value)}>
                {selectedUnit.modules.length === 0 && <option value="">No modules</option>}
                {unitTrainableMods.length > 0 && (
                  <option value="ALL">All trainable modules ({unitTrainableMods.length})</option>
                )}
                {selectedUnit.modules.map(m => (
                  <option key={m.id} value={m.id}>{m.name} ({m.model_display_name})</option>
                ))}
              </select>
            </label>
          ) : (
            <label className="block text-xs font-medium">
              AI Model <span className="text-red-500">*</span>
              <select className={FIELD} value={modelKey} onChange={e => setModelKey(e.target.value)}>
                {trainableModels.map(c => (
                  <option key={c.model_key} value={c.model_key} disabled={c.is_enabled === false}>
                    {c.display_name}{c.is_enabled === false ? ' (Disabled in Settings)' : ''}
                  </option>
                ))}
              </select>
            </label>
          )}

          {isAllModules ? (
            <label className="block text-xs font-medium">
              Batch Execution Mode
              <select className={FIELD} value={batchMode} onChange={e => setBatchMode(e.target.value as 'chained' | 'simultaneous')}>
                <option value="chained">Chained (one-by-one)</option>
                <option value="simultaneous">Simultaneous (parallel)</option>
              </select>
            </label>
          ) : null}

          <label className="block text-xs font-medium">
            {isAllModules ? 'Fallback dataset (if module has none)' : 'Training dataset'} <span className="text-red-500">*</span>
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
            Max epochs
            <input type="number" min={1} max={50} className={FIELD} value={maxEpochs} onChange={e => setMaxEpochs(Math.max(1, +e.target.value))} />
          </label>

          {!isAllModules && (
            <label className="block text-xs font-medium">
              Batches per epoch
              <input type="number" min={5} max={2000} className={FIELD} value={limitBatches} onChange={e => setLimitBatches(Math.max(5, +e.target.value))} />
            </label>
          )}
        </div>

        {(selectedModule || isAllModules) && (
          <div className="rounded-md border px-3 py-2.5 text-xs popup-subtle flex flex-wrap items-center gap-3">
            <Layers size={14} className="text-blue-500 shrink-0" />
            {isAllModules ? (
              <span>
                Batch training <strong>{unitTrainableMods.length} module(s)</strong> in <strong>{selectedUnit?.name}</strong> ({batchMode === 'chained' ? 'one-by-one' : 'simultaneous'}).
              </span>
            ) : (
              <span>
                Training from Scanner Unit config: <strong>{selectedUnit?.name}</strong> → <strong>{selectedModule?.name}</strong>
                {' '}· Model: <strong>{selectedModule?.model_display_name}</strong>
              </span>
            )}
          </div>
        )}

        <div className="flex items-center justify-between pt-1">
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Trains isolated checkpoints on GPU (CUDA) when available.
          </p>
          <Button size="sm" loading={starting} disabled={!!hasRunning || !!trainingIssue} onClick={handleStart}>
            <Play size={14} /> {hasRunning ? 'Job Running…' : isAllModules ? `Train All (${batchMode})` : 'Start Training'}
          </Button>
        </div>
      </section>

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
        <div className="space-y-4">
          {realtimeJobs.length === 0 ? (
            <section className="card p-5">
              <EmptyState title="No active or recent training runs" body="Start a training run above to watch live progress and logs." />
            </section>
          ) : (
            realtimeJobs.map(job => (
              <section key={job.id} className="card p-5 space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="font-semibold">RUN-{job.id} · {job.model_key}</h2>
                      <StatusBadge value={job.status} size="md" />
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                      Current stage: <strong>{job.current_step}</strong>
                    </p>
                  </div>
                  <span className="text-2xl font-semibold tabular-nums">{job.progress_pct}%</span>
                </div>

                <div className="h-2.5 w-full rounded-full overflow-hidden popup-subtle border" style={{ borderColor: 'var(--color-border)' }}>
                  <div
                    className={`h-full transition-all duration-500 ${
                      job.status === 'Failed' ? 'bg-red-600' :
                      job.status === 'Completed' ? 'bg-green-600' : 'bg-blue-600'
                    }`}
                    style={{ width: `${job.progress_pct}%` }}
                  />
                </div>

                {job.error_message && (
                  <div className="rounded bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-500">
                    {job.error_message}
                  </div>
                )}

                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: 'var(--color-text-secondary)' }}>
                    Live Execution Log
                  </h3>
                  <div className="rounded-md bg-slate-950 text-slate-200 p-3 font-mono text-xs max-h-52 overflow-y-auto space-y-1">
                    {job.logs.length === 0 ? (
                      <span className="text-slate-500">Waiting for logs…</span>
                    ) : (
                      job.logs.map((line, i) => <div key={i}>{line}</div>)
                    )}
                  </div>
                </div>
              </section>
            ))
          )}
        </div>
      ) : (
        <section className="card">
          {jobs && jobs.length === 0 ? (
            <EmptyState title="No training runs yet" body="Start a training run above to train your Scanner Unit module(s)." />
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
