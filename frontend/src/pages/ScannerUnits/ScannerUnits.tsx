/**
 * Scanner Units Management — Implements all 4 screens from CLOCKIT_Scanner_Unit_UI_Specification.md
 * with full light/dark theme support and no hardcoded industry/product presets.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Plus, RefreshCw, Cpu, Trash2, Edit2, Play, Upload, X, Layers,
} from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import {
  listScannerUnits,
  createScannerUnit,
  updateScannerUnit,
  deleteScannerUnit,
  addModule,
  updateModule,
  deleteModule,
  getModelCatalogue,
} from '../../services/scannerUnitService'
import { listDatasets, uploadDataset } from '../../services/datasetService'
import { classifyError } from '../../services/api'
import type {
  AnalysisModule,
  DatasetRecord,
  ModelCapability,
  ScannerUnit,
} from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'

export default function ScannerUnits() {
  const navigate = useNavigate()
  const [units, setUnits] = useState<ScannerUnit[]>()
  const [catalogue, setCatalogue] = useState<ModelCapability[]>([])
  const [datasets, setDatasets] = useState<DatasetRecord[]>([])
  const [err, setErr] = useState<string>()

  // Screen 1: Create / Rename Scanner Unit dialog
  const [createOpen, setCreateOpen] = useState(false)
  const [editingUnit, setEditingUnit] = useState<ScannerUnit | null>(null)
  const [unitName, setUnitName] = useState('')
  const [unitDesc, setUnitDesc] = useState('')
  const [unitIndustry, setUnitIndustry] = useState('')
  const [unitProduct, setUnitProduct] = useState('')
  const [unitBusy, setUnitBusy] = useState(false)
  const [unitErr, setUnitErr] = useState('')

  // Delete confirmations
  const [confirmDeleteUnit, setConfirmDeleteUnit] = useState<ScannerUnit | null>(null)
  const [confirmDeleteMod, setConfirmDeleteMod] = useState<AnalysisModule | null>(null)

  // Screen 3: Selected Scanner Unit Configuration Popup
  const [selectedUnit, setSelectedUnit] = useState<ScannerUnit | null>(null)

  // Screen 4: Module Add/Edit sub-view inside popup
  const [modMode, setModMode] = useState<'none' | 'create' | 'edit'>('none')
  const [editingMod, setEditingMod] = useState<AnalysisModule | null>(null)
  const [modName, setModName] = useState('')
  const [modDesc, setModDesc] = useState('')
  const [modPurpose, setModPurpose] = useState('')
  const [modModelKey, setModModelKey] = useState('efficientad_small')
  const [modDatasetId, setModDatasetId] = useState<number | ''>('')
  const [modOutputs, setModOutputs] = useState<string[]>(['anomaly_score', 'heatmap'])
  const [modDirty, setModDirty] = useState(false)
  const [modBusy, setModBusy] = useState(false)
  const [modErr, setModErr] = useState('')

  // Inline dataset upload inside Screen 4
  const [inlineFiles, setInlineFiles] = useState<File[]>([])
  const [inlineDsName, setInlineDsName] = useState('')
  const [uploadingDs, setUploadingDs] = useState(false)
  const [uploadDsErr, setUploadDsErr] = useState('')

  // Unsaved changes guard
  const [unsavedPromptOpen, setUnsavedPromptOpen] = useState(false)
  const [pendingCloseTarget, setPendingCloseTarget] = useState<'module' | 'popup'>('module')

  const loadAll = async () => {
    setErr(undefined)
    try {
      const [u, c, d] = await Promise.all([
        listScannerUnits(),
        getModelCatalogue(),
        listDatasets(),
      ])
      setUnits(u)
      setCatalogue(c)
      setDatasets(d)
      if (selectedUnit) {
        const refreshed = u.find(x => x.id === selectedUnit.id) ?? null
        setSelectedUnit(refreshed)
      }
    } catch (e) {
      setErr(classifyError(e).message)
    }
  }

  useEffect(() => { void loadAll() }, [])

  // ── Screen 1: Create / Edit Scanner Unit ──────────────────────────────────
  const openCreateUnit = () => {
    setEditingUnit(null)
    setUnitName('')
    setUnitDesc('')
    setUnitIndustry('')
    setUnitProduct('')
    setUnitErr('')
    setCreateOpen(true)
  }

  const openEditUnit = (u: ScannerUnit) => {
    setEditingUnit(u)
    setUnitName(u.name)
    setUnitDesc(u.description ?? '')
    setUnitIndustry(u.industry)
    setUnitProduct(u.product_name ?? '')
    setUnitErr('')
    setCreateOpen(true)
  }

  const submitUnit = async () => {
    if (!unitName.trim()) {
      setUnitErr('Scanner Unit name is required.')
      return
    }
    setUnitBusy(true)
    setUnitErr('')
    try {
      if (editingUnit) {
        const updated = await updateScannerUnit(editingUnit.id, {
          name: unitName.trim(),
          description: unitDesc.trim() || undefined,
          industry: unitIndustry.trim() || 'General',
          product_name: unitProduct.trim() || undefined,
        })
        setCreateOpen(false)
        await loadAll()
        if (selectedUnit?.id === updated.id) setSelectedUnit(updated)
      } else {
        const created = await createScannerUnit({
          name: unitName.trim(),
          description: unitDesc.trim() || undefined,
          industry: unitIndustry.trim() || 'General',
          product_name: unitProduct.trim() || undefined,
        })
        setCreateOpen(false)
        await loadAll()
        setSelectedUnit(created)
        setModMode('none')
      }
    } catch (e) {
      setUnitErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setUnitBusy(false)
    }
  }

  const handleDeleteUnit = async () => {
    if (!confirmDeleteUnit) return
    await deleteScannerUnit(confirmDeleteUnit.id)
    if (selectedUnit?.id === confirmDeleteUnit.id) setSelectedUnit(null)
    setConfirmDeleteUnit(null)
    await loadAll()
  }

  // ── Screen 4: Module Add / Edit ───────────────────────────────────────────
  const selectedCap = catalogue.find(m => m.model_key === modModelKey)

  const openAddModule = () => {
    const defaultCap = catalogue.find(m => m.integration_state === 'available_integrated') ?? catalogue[0]
    setEditingMod(null)
    setModName('')
    setModDesc('')
    setModPurpose('')
    setModModelKey(defaultCap?.model_key ?? 'efficientad_small')
    setModDatasetId('')
    setModOutputs(defaultCap ? defaultCap.supported_outputs.map(o => o.key) : ['anomaly_score'])
    setModDirty(false)
    setModErr('')
    setInlineFiles([])
    setInlineDsName('')
    setUploadDsErr('')
    setModMode('create')
  }

  const openEditModule = (m: AnalysisModule) => {
    setEditingMod(m)
    setModName(m.name)
    setModDesc(m.description ?? '')
    setModPurpose(m.purpose ?? '')
    setModModelKey(m.model_key)
    setModDatasetId(m.dataset_id ?? '')
    setModOutputs(m.selected_outputs)
    setModDirty(false)
    setModErr('')
    setInlineFiles([])
    setInlineDsName('')
    setUploadDsErr('')
    setModMode('edit')
  }

  const handleModelChange = (newKey: string) => {
    setModModelKey(newKey)
    setModDirty(true)
    const cap = catalogue.find(c => c.model_key === newKey)
    if (cap) {
      const allowed = new Set(cap.supported_outputs.map(o => o.key))
      const kept = modOutputs.filter(o => allowed.has(o))
      setModOutputs(kept.length > 0 ? kept : cap.supported_outputs.slice(0, 2).map(o => o.key))
    }
  }

  const toggleOutput = (key: string) => {
    setModDirty(true)
    setModOutputs(prev => prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key])
  }

  const handleInlineDatasetUpload = async () => {
    if (!inlineFiles.length) return
    const dsLabel = inlineDsName.trim() || `${selectedUnit?.name ?? 'Scanner'} Dataset`
    setUploadingDs(true)
    setUploadDsErr('')
    try {
      const ds = await uploadDataset(
        { name: dsLabel, category: 'normal', industry: selectedUnit?.industry ?? 'General' },
        inlineFiles,
      )
      setDatasets(prev => [ds, ...prev])
      setModDatasetId(ds.id)
      setInlineFiles([])
      setInlineDsName('')
      setModDirty(true)
    } catch (e) {
      setUploadDsErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setUploadingDs(false)
    }
  }

  const saveModule = async () => {
    if (!selectedUnit) return
    if (!modName.trim()) {
      setModErr('Module name is required.')
      return
    }
    if (modOutputs.length === 0) {
      setModErr('Select at least one supported output.')
      return
    }
    setModBusy(true)
    setModErr('')
    try {
      const payload = {
        name: modName.trim(),
        description: modDesc.trim() || undefined,
        purpose: modPurpose.trim() || undefined,
        model_key: modModelKey,
        dataset_id: modDatasetId === '' ? null : Number(modDatasetId),
        selected_outputs: modOutputs,
      }
      if (modMode === 'edit' && editingMod) {
        await updateModule(selectedUnit.id, editingMod.id, payload)
      } else {
        await addModule(selectedUnit.id, payload)
      }
      setModDirty(false)
      setModMode('none')
      await loadAll()
    } catch (e) {
      setModErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setModBusy(false)
    }
  }

  const requestCloseModule = () => {
    if (modDirty) {
      setPendingCloseTarget('module')
      setUnsavedPromptOpen(true)
    } else {
      setModMode('none')
    }
  }

  const requestClosePopup = () => {
    if (modMode !== 'none' && modDirty) {
      setPendingCloseTarget('popup')
      setUnsavedPromptOpen(true)
    } else {
      setModMode('none')
      setSelectedUnit(null)
    }
  }

  const handleDeleteModule = async () => {
    if (!selectedUnit || !confirmDeleteMod) return
    await deleteModule(selectedUnit.id, confirmDeleteMod.id)
    setConfirmDeleteMod(null)
    await loadAll()
  }

  if (!units && !err) return <LoadingState message="Loading Scanner Units…" />
  if (err) return <ErrorState message="Failed to load Scanner Units" detail={err} onRetry={loadAll} />

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <h1>Scanner Units</h1>
          <p>Create and configure reusable inspection Scanner Units and their Analysis Modules.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={loadAll}><RefreshCw size={14} />Refresh</Button>
          <Button size="sm" onClick={openCreateUnit}><Plus size={14} />Create Scanner Unit</Button>
        </div>
      </div>

      {units && units.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No Scanner Units yet"
            body="A Scanner Unit groups one or more AI analysis modules into a reusable inspection workflow."
            action={<Button size="sm" onClick={openCreateUnit}><Plus size={14} />Create Scanner Unit</Button>}
          />
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {units?.map(u => (
            <div
              key={u.id}
              role="button"
              tabIndex={0}
              onClick={() => { setSelectedUnit(u); setModMode('none') }}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedUnit(u); setModMode('none') } }}
              className="card p-4 cursor-pointer hover:border-blue-400 transition-colors text-left"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-semibold" style={{ color: 'var(--color-text-primary)' }}>{u.name}</h2>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                    {u.industry}{u.product_name ? ` · ${u.product_name}` : ''}
                  </p>
                </div>
                <StatusBadge value={u.status} />
              </div>

              {u.description && (
                <p className="mt-2 text-xs line-clamp-2" style={{ color: 'var(--color-text-secondary)' }}>{u.description}</p>
              )}

              <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs" style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
                <span className="flex items-center gap-1">
                  <Layers size={13} /> {u.module_count} module{u.module_count !== 1 ? 's' : ''}
                </span>
                <span>Updated {new Date(u.updated_at).toLocaleDateString()}</span>
              </div>

              <div className="mt-3 flex gap-2" onClick={e => e.stopPropagation()}>
                <Button size="sm" variant="secondary" onClick={() => { setSelectedUnit(u); setModMode('none') }}>
                  Configure
                </Button>
                <Button size="sm" variant="ghost" onClick={() => openEditUnit(u)} aria-label={`Rename ${u.name}`}>
                  <Edit2 size={13} />
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setConfirmDeleteUnit(u)} aria-label={`Delete ${u.name}`}>
                  <Trash2 size={13} className="text-red-500" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Scanner Unit Dialog */}
      <Modal
        open={createOpen}
        title={editingUnit ? 'Edit Scanner Unit' : 'Create Scanner Unit'}
        confirmLabel={editingUnit ? 'Save Changes' : 'Create Scanner Unit'}
        onCancel={() => setCreateOpen(false)}
        onConfirm={submitUnit}
        confirmLoading={unitBusy}
      >
        <div className="space-y-3">
          {unitErr && <p className="text-xs text-red-500 bg-red-500/10 px-3 py-2 rounded">{unitErr}</p>}
          <label className="block text-sm font-medium">
            Name <span className="text-red-500">*</span>
            <input className={FIELD} value={unitName} onChange={e => setUnitName(e.target.value)} placeholder="e.g. Front Surface Scanner" />
          </label>
          <label className="block text-sm font-medium">
            Description
            <textarea className={FIELD} rows={2} value={unitDesc} onChange={e => setUnitDesc(e.target.value)} placeholder="Optional purpose or station notes" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm font-medium">
              Industry
              <input className={FIELD} value={unitIndustry} onChange={e => setUnitIndustry(e.target.value)} placeholder="e.g. Steel, Textile, Custom" />
            </label>
            <label className="block text-sm font-medium">
              Product / Part
              <input className={FIELD} value={unitProduct} onChange={e => setUnitProduct(e.target.value)} placeholder="e.g. Part-101" />
            </label>
          </div>
        </div>
      </Modal>

      {/* Screen 3 & 4: Scanner Unit Configuration Popup (Dark-theme compatible) */}
      {selectedUnit && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal>
          <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-lg shadow-2xl popup-surface">
            {/* Popup header */}
            <div className="flex items-center justify-between border-b px-5 py-4" style={{ borderColor: 'var(--color-border)' }}>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    {modMode === 'none' ? selectedUnit.name : modMode === 'create' ? 'Add Analysis Module' : 'Edit Analysis Module'}
                  </h2>
                  <StatusBadge value={selectedUnit.status} />
                </div>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                  {selectedUnit.industry}{selectedUnit.product_name ? ` · ${selectedUnit.product_name}` : ''}
                  {selectedUnit.description ? ` — ${selectedUnit.description}` : ''}
                </p>
              </div>
              <button onClick={requestClosePopup} className="rounded p-1 hover:opacity-80" style={{ color: 'var(--color-text-secondary)' }} aria-label="Close popup">
                <X size={18} />
              </button>
            </div>

            {/* Popup body */}
            <div className="flex-1 overflow-y-auto p-5">
              {modMode === 'none' ? (
                /* ── Screen 3: Module List (single Add Module button) ─────── */
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                      Analysis Modules ({selectedUnit.modules.length})
                    </h3>
                    <div className="flex gap-2">
                      {selectedUnit.modules.some(m => m.state === 'Ready') && (
                        <Button size="sm" variant="secondary" onClick={() => navigate(`/test-sample?scannerId=${selectedUnit.id}`)}>
                          <Play size={13} /> Test Sample
                        </Button>
                      )}
                      <Button size="sm" onClick={openAddModule}>
                        <Plus size={14} /> Add Module
                      </Button>
                    </div>
                  </div>

                  {selectedUnit.modules.length === 0 ? (
                    <EmptyState
                      title="No analysis modules configured"
                      body="Click Add Module above to configure what this Scanner Unit inspects."
                    />
                  ) : (
                    <div className="space-y-2">
                      {selectedUnit.modules.map(m => (
                        <div key={m.id} className="rounded-md border p-3 flex flex-wrap items-center justify-between gap-3 popup-subtle">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>{m.name}</span>
                              <StatusBadge value={m.state} />
                            </div>
                            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                              Model: <strong>{m.model_display_name}</strong>
                              {m.purpose ? ` · ${m.purpose}` : ''}
                              {m.dataset_name ? ` · Dataset: ${m.dataset_name} (${m.dataset_validation_status})` : ''}
                            </p>
                            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                              Outputs: {m.selected_outputs.join(', ')}
                            </p>
                          </div>
                          <div className="flex items-center gap-1.5">
                            {m.model_key === 'efficientad_small' && (
                              <Button size="sm" variant="secondary" onClick={() => navigate(`/training?unitId=${selectedUnit.id}&moduleId=${m.id}`)}>
                                Train
                              </Button>
                            )}
                            <Button size="sm" variant="ghost" onClick={() => openEditModule(m)}>
                              <Edit2 size={13} /> Edit
                            </Button>
                            <Button size="sm" variant="ghost" onClick={() => setConfirmDeleteMod(m)} aria-label="Remove module">
                              <Trash2 size={13} className="text-red-500" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                /* ── Screen 4: Analysis Module Add / Edit Form ────────────── */
                <div className="space-y-5">
                  {modErr && (
                    <div className="rounded-md bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-500">
                      {modErr}
                    </div>
                  )}

                  {/* 1. Module Details */}
                  <section className="space-y-3">
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                      1. Module details
                    </h3>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="block text-sm font-medium">
                        Module name <span className="text-red-500">*</span>
                        <input className={FIELD} value={modName} onChange={e => { setModName(e.target.value); setModDirty(true) }} placeholder="e.g. Surface Anomaly Detector" />
                      </label>
                      <label className="block text-sm font-medium">
                        Purpose / category
                        <input className={FIELD} value={modPurpose} onChange={e => { setModPurpose(e.target.value); setModDirty(true) }} placeholder="e.g. Crack / Surface Detection" />
                      </label>
                    </div>
                    <label className="block text-sm font-medium">
                      Description
                      <input className={FIELD} value={modDesc} onChange={e => { setModDesc(e.target.value); setModDirty(true) }} placeholder="Optional notes about what this module checks" />
                    </label>
                  </section>

                  {/* 2. AI Model Selection (dark-theme friendly) */}
                  <section className="space-y-2 border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                      2. AI model selection
                    </h3>
                    <div className="grid gap-2">
                      {catalogue.map(cap => {
                        const integrated = cap.integration_state === 'available_integrated'
                        const active = modModelKey === cap.model_key
                        return (
                          <label
                            key={cap.model_key}
                            className={`flex items-start gap-3 rounded-md border p-3 text-sm transition-colors ${
                              !integrated ? 'opacity-65 cursor-not-allowed popup-subtle' :
                              active ? 'border-blue-500 bg-blue-500/10 cursor-pointer' : 'cursor-pointer popup-subtle hover:border-blue-400'
                            }`}
                          >
                            <input
                              type="radio"
                              name="model_key"
                              value={cap.model_key}
                              checked={active}
                              disabled={!integrated}
                              onChange={() => handleModelChange(cap.model_key)}
                              className="mt-1 accent-blue-600"
                            />
                            <div className="flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <Cpu size={14} style={{ color: 'var(--color-text-secondary)' }} />
                                <span className="font-medium" style={{ color: 'var(--color-text-primary)' }}>{cap.display_name}</span>
                                <span className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{cap.model_family}</span>
                                {integrated ? (
                                  <StatusBadge value={cap.ready_for_inference ? 'Ready' : 'Configured'} />
                                ) : (
                                  <StatusBadge value="Unavailable" />
                                )}
                              </div>
                              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>{cap.task}</p>
                              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{cap.dataset_requirements}</p>
                              <p className="text-xs text-amber-500 mt-0.5">{cap.limitations}</p>
                            </div>
                          </label>
                        )
                      })}
                    </div>
                  </section>

                  {/* 3. Dataset and Files */}
                  <section className="space-y-3 border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                      3. Dataset & files
                    </h3>
                    {selectedCap && !selectedCap.requires_dataset ? (
                      <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                        This heuristic method does not require a training dataset.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        <label className="block text-sm font-medium">
                          Select existing validated dataset
                          <select
                            className={FIELD}
                            value={modDatasetId}
                            onChange={e => { setModDatasetId(e.target.value ? Number(e.target.value) : ''); setModDirty(true) }}
                          >
                            <option value="">None selected</option>
                            {datasets.map(ds => (
                              <option key={ds.id} value={ds.id}>
                                {ds.name} — {ds.valid_image_count} images ({ds.validation_status})
                              </option>
                            ))}
                          </select>
                        </label>

                        <div className="rounded-md border border-dashed p-3 space-y-2 popup-subtle">
                          <p className="text-xs font-medium">Or upload a new dataset (.zip or images)</p>
                          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                            ZIP must contain only root-level images (no subfolders). All images are standardized to 480p (640×480).
                          </p>
                          <div className="flex flex-wrap gap-2 items-center">
                            <input
                              className="px-2.5 py-1.5 text-xs flex-1 min-w-[160px] input-field"
                              placeholder="Dataset name"
                              value={inlineDsName}
                              onChange={e => setInlineDsName(e.target.value)}
                            />
                            <label className="cursor-pointer rounded border px-2.5 py-1.5 text-xs flex items-center gap-1 input-field hover:opacity-90">
                              <Upload size={13} />
                              {inlineFiles.length > 0 ? `${inlineFiles.length} file(s)` : 'Choose files / ZIP'}
                              <input
                                type="file"
                                multiple
                                accept=".zip,image/*"
                                className="sr-only"
                                onChange={e => setInlineFiles(Array.from(e.target.files ?? []))}
                              />
                            </label>
                            <Button
                              size="sm"
                              variant="secondary"
                              disabled={inlineFiles.length === 0 || uploadingDs}
                              loading={uploadingDs}
                              onClick={handleInlineDatasetUpload}
                            >
                              Upload & Validate
                            </Button>
                          </div>
                          {uploadDsErr && <p className="text-xs text-red-500">{uploadDsErr}</p>}
                        </div>
                      </div>
                    )}
                  </section>

                  {/* 4. Output Configuration */}
                  <section className="space-y-2 border-t pt-4" style={{ borderColor: 'var(--color-border)' }}>
                    <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
                      4. Output configuration
                    </h3>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {selectedCap?.supported_outputs.map(out => (
                        <label key={out.key} className="flex items-start gap-2 rounded border p-2.5 cursor-pointer popup-subtle">
                          <input
                            type="checkbox"
                            checked={modOutputs.includes(out.key)}
                            onChange={() => toggleOutput(out.key)}
                            className="mt-0.5 accent-blue-600"
                          />
                          <div>
                            <div className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>{out.label}</div>
                            <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{out.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  </section>
                </div>
              )}
            </div>

            {/* Popup Footer */}
            <div className="flex items-center justify-between border-t px-5 py-3 popup-subtle rounded-b-lg" style={{ borderColor: 'var(--color-border)' }}>
              {modMode === 'none' ? (
                <>
                  <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    Saved changes persist automatically.
                  </span>
                  <Button variant="secondary" size="sm" onClick={requestClosePopup}>Close</Button>
                </>
              ) : (
                <>
                  <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    Saving configuration does not auto-trigger training.
                  </span>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm" onClick={requestCloseModule}>Cancel</Button>
                    <Button size="sm" loading={modBusy} onClick={saveModule}>
                      {modMode === 'edit' ? 'Save Changes' : 'Save Module'}
                    </Button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Unsaved changes confirmation */}
      <Modal
        open={unsavedPromptOpen}
        title="Discard unsaved changes?"
        confirmLabel="Discard changes"
        cancelLabel="Continue editing"
        dangerous
        onCancel={() => setUnsavedPromptOpen(false)}
        onConfirm={() => {
          setUnsavedPromptOpen(false)
          setModDirty(false)
          setModMode('none')
          if (pendingCloseTarget === 'popup') setSelectedUnit(null)
        }}
      >
        You have unsaved changes in the Analysis Module editor. Leaving now will discard them.
      </Modal>

      {/* Delete Scanner Unit confirmation */}
      <Modal
        open={!!confirmDeleteUnit}
        title="Delete Scanner Unit?"
        confirmLabel="Delete Scanner Unit"
        dangerous
        onCancel={() => setConfirmDeleteUnit(null)}
        onConfirm={handleDeleteUnit}
      >
        Delete <strong>{confirmDeleteUnit?.name}</strong> and its {confirmDeleteUnit?.module_count} module(s)?
        Existing inspection history records will be preserved.
      </Modal>

      {/* Delete Module confirmation */}
      <Modal
        open={!!confirmDeleteMod}
        title="Remove Analysis Module?"
        confirmLabel="Remove Module"
        dangerous
        onCancel={() => setConfirmDeleteMod(null)}
        onConfirm={handleDeleteModule}
      >
        Remove <strong>{confirmDeleteMod?.name}</strong> from this Scanner Unit? Uploaded datasets and trained artifacts will not be deleted.
      </Modal>
    </div>
  )
}
