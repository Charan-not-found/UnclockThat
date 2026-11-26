/**
 * AI Models registry — lifecycle-aware, real data only.
 * No records created on load. Downloaded weights shown as "not ready" until trained.
 */
import { useEffect, useState } from 'react'
import { RefreshCw, Info } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listModels, toggleModel } from '../../services/modelService'
import { getModelCatalogue } from '../../services/scannerUnitService'
import type { ModelCapability, ModelInfo } from '../../types'

const FAMILY_LABEL: Record<string, string> = {
  efficientad:      'EfficientAD (Anomaly)',
  yolo_seg:         'YOLO-Seg (Localisation)',
  patchcore:        'PatchCore (Anomaly)',
  dinomaly:         'Dinomaly (ViT Anomaly)',
  anomalydino:      'AnomalyDINO (Few-Shot ViT)',
  omniposead:       'OmniPoseAD (Pose-Agnostic)',
  mobilenet:        'MobileNet (Classification)',
  opencv_heuristic: 'OpenCV Heuristic (Prototype)',
}

export default function Models() {
  const [catalogue, setCatalogue] = useState<ModelCapability[]>([])
  const [models, setModels] = useState<ModelInfo[]>()
  const [err, setErr] = useState(false)
  const [toggling, setToggling] = useState<string>()

  const load = () => {
    setErr(false)
    setModels(undefined)
    Promise.all([getModelCatalogue(), listModels()])
      .then(([cat, regs]) => {
        setCatalogue(cat)
        setModels(regs)
      })
      .catch(() => setErr(true))
  }

  useEffect(load, [])

  const handleToggle = async (m: ModelInfo) => {
    setToggling(m.id)
    try {
      const updated = await toggleModel(m.id)
      setModels(prev => prev?.map(x => x.id === m.id ? updated : x))
    } catch {
      /* keep existing state */
    } finally {
      setToggling(undefined)
    }
  }

  if (!models && !err) return <LoadingState message="Loading model registry…" />
  if (err) return <ErrorState message="Failed to load model registry" onRetry={load} />

  const enabledCatalogue = catalogue.filter(
    c => c.integration_state !== 'disabled_by_admin' && c.is_enabled !== false,
  )
  const enabledFamilies = new Set(enabledCatalogue.map(c => c.model_family))
  const visibleModels = models?.filter(m => enabledFamilies.size === 0 || enabledFamilies.has(m.model_family))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>AI Models</h1>
            <PageHelpLegend
              title="AI Models"
              summary="Lists enabled base models and cloned per-module models with live on-disk weight verification."
              items={[
                { label: 'Ready', badge: 'Ready', description: 'Model is active and available for inspection.' },
                { label: 'Disabled', badge: 'Disabled', description: 'Model is inactive until trained or manually enabled.' },
                { label: '✓ Present', description: 'Weight/checkpoint file exists on disk.' },
                { label: '✗ Missing', description: 'Weights file not found; run scripts/install_models.py or train the module.' },
              ]}
            />
          </div>
          <p>
            {enabledCatalogue.length} enabled base model{enabledCatalogue.length !== 1 ? 's' : ''} · {visibleModels?.length ?? 0} custom/registered module model{visibleModels?.length !== 1 ? 's' : ''}.
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {/* Base Model Library (enabled models from catalogue) */}
      <section className="card">
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <h2 className="font-medium text-sm">Base AI Model Library ({enabledCatalogue.length})</h2>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
            Showing enabled models only. Manage model visibility in <a href="/settings" className="text-blue-500 hover:underline">Settings</a>.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th>Model</th>
                <th>Family</th>
                <th>Capability &amp; Speed</th>
                <th>Paradigm</th>
                <th>Status</th>
                <th>Base Weights</th>
              </tr>
            </thead>
            <tbody>
              {enabledCatalogue.map(c => (
                <tr key={c.model_key}>
                  <td className="font-medium">{c.display_name}</td>
                  <td className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {FAMILY_LABEL[c.model_family] ?? c.model_family}
                  </td>
                  <td className="text-xs max-w-md" style={{ color: 'var(--color-text-secondary)' }}>
                    {c.task}
                  </td>
                  <td className="font-mono text-xs">{c.training_paradigm}</td>
                  <td>
                    <StatusBadge
                      value={
                        c.integration_state === 'disabled_by_admin'
                          ? 'Disabled'
                          : c.ready_for_inference
                          ? 'Ready'
                          : 'Configured'
                      }
                    />
                  </td>
                  <td className="text-xs">
                    {c.pretrained_present ? (
                      <span className="text-green-600 font-medium">✓ Present</span>
                    ) : (
                      <span className="text-amber-500 font-medium">Needs setup</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Model readiness summary */}
      <div className="card px-4 py-3 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-2">
          <Info size={16} className="text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-blue-800 space-y-1">
            <p>
              <strong>Model readiness:</strong>{' '}
              {models && models.some(m => m.enabled)
                ? `Active (Ready): ${models.filter(m => m.enabled).map(m => m.name).join(', ')}. `
                : 'No models are currently active. '}
              Un-trained pretrained weights remain <em>Disabled</em> until trained.
            </p>
            <p>To register default models, use Administration or <code className="bg-blue-100 px-1 rounded">POST /api/v1/admin/seed</code>.</p>
          </div>
        </div>
      </div>

      {models?.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No models registered"
            body="Run the admin seed to register the downloaded pretrained weights."
            action={
              <a href="/admin" className="text-sm text-blue-600 hover:underline">Go to Administration →</a>
            }
          />
        </div>
      ) : (
        <section className="card">
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Name</th><th>Family</th><th>Task</th><th>Version</th>
                  <th>State</th><th>Weights</th><th>Action</th>
                </tr>
              </thead>
              <tbody>
                {visibleModels?.map(m => (
                  <tr key={m.id}>
                    <td className="font-medium">{m.name}</td>
                    <td className="text-slate-500 text-xs">{FAMILY_LABEL[m.model_family] ?? m.model_family}</td>
                    <td className="text-slate-500">{m.task}</td>
                    <td className="tabular-nums font-mono text-xs">{m.version}</td>
                    <td><StatusBadge value={m.state} /></td>
                    <td>
                      {m.weights_path ? (
                        <span className={`text-xs font-medium ${m.has_weights_file ? 'text-green-700' : 'text-red-600'}`}>
                          {m.has_weights_file ? '✓ Present' : '✗ Missing'}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">N/A</span>
                      )}
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        size="sm"
                        loading={toggling === m.id}
                        onClick={() => handleToggle(m)}
                      >
                        {m.enabled ? 'Disable' : 'Enable'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Detail cards for downloaded weights */}
      {models && models.filter(m => m.weights_path).length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-slate-700 mb-2">Registered artifact details</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {models.filter(m => m.weights_path).map(m => (
              <div key={m.id} className="card p-3">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium text-sm">{m.name}</p>
                  <StatusBadge value={m.state} size="sm" />
                </div>
                <p className="text-xs text-slate-400 mt-1">{m.task}</p>
                <div className="mt-2 text-xs space-y-1">
                  <div>
                    <span className="text-slate-400">Weights file: </span>
                    <span className="font-mono break-all">{m.weights_path || '—'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400">File on disk: </span>
                    <span className={m.has_weights_file ? 'text-green-700' : 'text-red-600'}>
                      {m.has_weights_file ? 'Present' : 'Not found'}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
