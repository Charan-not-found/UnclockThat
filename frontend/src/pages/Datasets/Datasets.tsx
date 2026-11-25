/**
 * Datasets page — real upload (.zip or images), validation, and dataset management.
 * No inbuilt industry presets — free-text industry input.
 */
import { useEffect, useState } from 'react'
import { Upload, RefreshCw, Trash2, CheckCircle2, AlertCircle } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listDatasets, uploadDataset, validateDataset, deleteDataset } from '../../services/datasetService'
import { classifyError } from '../../services/api'
import type { DatasetRecord } from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'

export default function Datasets() {
  const [rows, setRows] = useState<DatasetRecord[]>()
  const [err, setErr] = useState<string>()
  const [name, setName] = useState('')
  const [category, setCategory] = useState('normal')
  const [industry, setIndustry] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [uploadErr, setUploadErr] = useState('')
  const [validatingId, setValidatingId] = useState<number>()
  const [deleteTarget, setDeleteTarget] = useState<DatasetRecord | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteErr, setDeleteErr] = useState('')

  const load = async () => {
    setErr(undefined)
    try {
      setRows(await listDatasets())
    } catch (e) {
      setErr(classifyError(e).message)
    }
  }

  useEffect(() => { void load() }, [])

  const handleUpload = async () => {
    if (!name.trim()) {
      setUploadErr('Dataset name is required.')
      return
    }
    if (files.length === 0) {
      setUploadErr('Select a .zip archive or image files to upload.')
      return
    }
    setUploading(true)
    setUploadErr('')
    try {
      await uploadDataset({ name: name.trim(), category, industry: industry.trim() || 'General' }, files)
      setName('')
      setIndustry('')
      setFiles([])
      await load()
    } catch (e) {
      setUploadErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setUploading(false)
    }
  }

  const handleRevalidate = async (id: number) => {
    setValidatingId(id)
    try {
      const updated = await validateDataset(id)
      setRows(prev => prev?.map(r => r.id === id ? updated : r))
    } finally {
      setValidatingId(undefined)
    }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteErr('')
    try {
      await deleteDataset(deleteTarget.id)
      setDeleteTarget(null)
      await load()
    } catch (e) {
      setDeleteErr(classifyError(e).detail || classifyError(e).message)
    } finally {
      setDeleting(false)
    }
  }

  if (!rows && !err) return <LoadingState message="Loading datasets…" />
  if (err) return <ErrorState message="Failed to load datasets" detail={err} onRetry={load} />

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Datasets</h1>
            <PageHelpLegend
              title="Datasets"
              summary="Datasets are stored in data/datasets/ and standardized to 480p (640×480) in data/training/."
              items={[
                { label: 'Validated', badge: 'Validated', description: 'Flat image-only archive or images verified and standardized to 480p.' },
                { label: 'Validation failed', badge: 'Validation failed', description: 'Dataset is empty, has subfolders, or contains non-image/corrupt files.' },
                { label: 'Duplicates', description: 'Exact SHA-256 content duplicates detected inside the upload.' },
              ]}
            />
          </div>
          <p>Upload, extract, and validate image datasets (.zip or image files) stored in <code>data/datasets/</code> and <code>data/training/</code>.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      <section className="card p-4 space-y-3">
        <div>
          <h2 className="font-medium text-sm">Upload & Validate Dataset</h2>
          <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
            ZIP archives must contain <strong>only images at the root</strong> (no subfolders or other files, e.g. <code>data.zip → [1.png, 2.png]</code>). All images are standardized to <strong>480p (640×480)</strong>.
          </p>
        </div>
        {uploadErr && (
          <div className="flex items-center gap-2 rounded bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-500">
            <AlertCircle size={14} /> {uploadErr}
          </div>
        )}
        <div className="grid gap-3 md:grid-cols-4">
          <label className="block text-xs font-medium">
            Dataset name <span className="text-red-500">*</span>
            <input className={FIELD} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Normal Batch 1" />
          </label>
          <label className="block text-xs font-medium">
            Category
            <select className={FIELD} value={category} onChange={e => setCategory(e.target.value)}>
              <option value="normal">Normal / defect-free</option>
              <option value="defective">Defective</option>
              <option value="mixed">Mixed</option>
              <option value="unlabelled">Unlabelled</option>
            </select>
          </label>
          <label className="block text-xs font-medium">
            Industry
            <input className={FIELD} value={industry} onChange={e => setIndustry(e.target.value)} placeholder="e.g. Steel, Textile, Custom" />
          </label>
          <div className="flex flex-col justify-end">
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-dashed px-3 py-2 text-xs font-medium input-field hover:opacity-90">
              <Upload size={14} />
              {files.length > 0 ? `${files.length} file(s) selected` : 'Choose ZIP or images'}
              <input type="file" multiple accept=".zip,image/*" className="sr-only" onChange={e => setFiles(Array.from(e.target.files ?? []))} />
            </label>
          </div>
        </div>
        <div className="flex justify-end">
          <Button size="sm" loading={uploading} onClick={handleUpload} disabled={files.length === 0}>
            <Upload size={14} /> Upload & Validate
          </Button>
        </div>
      </section>

      <section className="card">
        {rows && rows.length === 0 ? (
          <EmptyState
            title="No uploaded datasets yet"
            body="Upload a ZIP archive or image folder above to validate it for training."
          />
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Name</th><th>Category</th><th>Industry</th><th>Status</th>
                  <th className="tabular-nums">Valid Images</th>
                  <th className="tabular-nums">Invalid</th>
                  <th className="tabular-nums">Duplicates</th>
                  <th>Created</th><th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows?.map(ds => (
                  <tr key={ds.id}>
                    <td>
                      <p className="font-medium">{ds.name}</p>
                      <p className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>{ds.source_filename}</p>
                    </td>
                    <td className="text-xs">{ds.category}</td>
                    <td className="text-xs">{ds.industry}</td>
                    <td><StatusBadge value={ds.validation_status} /></td>
                    <td className="tabular-nums font-medium">{ds.valid_image_count}</td>
                    <td className="tabular-nums">{ds.invalid_file_count}</td>
                    <td className="tabular-nums">{ds.duplicate_count}</td>
                    <td className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{new Date(ds.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="flex items-center gap-1">
                        <Button type="button" size="sm" variant="ghost" loading={validatingId === ds.id} onClick={() => handleRevalidate(ds.id)}>
                          <CheckCircle2 size={13} /> Validate
                        </Button>
                        <Button type="button" size="sm" variant="ghost" onClick={() => { setDeleteErr(''); setDeleteTarget(ds) }} aria-label={`Delete ${ds.name}`}>
                          <Trash2 size={13} className="text-red-500" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <Modal
        open={!!deleteTarget}
        title="Delete Dataset?"
        confirmLabel="Delete"
        dangerous
        confirmLoading={deleting}
        onCancel={() => { setDeleteErr(''); setDeleteTarget(null) }}
        onConfirm={handleDelete}
      >
        <div className="space-y-2">
          <p>Delete dataset <strong>{deleteTarget?.name}</strong> and its extracted training files?</p>
          {deleteErr && <p className="text-xs text-red-500">{deleteErr}</p>}
        </div>
      </Modal>
    </div>
  )
}
