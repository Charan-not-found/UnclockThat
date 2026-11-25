/**
 * Test Sample page (replaces New Inspection) — test an uploaded sample image
 * against a configured Scanner Unit or active trained model.
 * No inbuilt industry or product presets.
 */
import { useEffect, useState, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Upload, Play, CheckCircle2, AlertCircle } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { ErrorState } from '../../components/common/LoadingState'
import { runInspection, reviewInspection } from '../../services/inspectionService'
import { listScannerUnits } from '../../services/scannerUnitService'
import type { InspectionRunResult, ScannerUnit } from '../../types'

const FIELD = 'mt-1 w-full px-3 py-2 text-sm input-field focus:border-blue-500 focus:outline-none'

const FEEDBACK_CATEGORIES = [
  'Correct detection',
  'False positive',
  'False negative',
  'Incorrect localization',
  'Incorrect class',
  'Uncertain',
]

export default function Inspection() {
  const [searchParams] = useSearchParams()
  const [scanners, setScanners] = useState<ScannerUnit[]>([])
  const [scannerId, setScannerId] = useState<string>(searchParams.get('scannerId') ?? '')
  const [threshold, setThreshold] = useState(0.5)
  const [file, setFile] = useState<File>()
  const [previewUrl, setPreviewUrl] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<InspectionRunResult>()
  const [err, setErr] = useState<string>()
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewDecision, setReviewDecision] = useState<'Approved' | 'Rejected'>('Approved')
  const [feedbackCat, setFeedbackCat] = useState('Correct detection')
  const [reviewNote, setReviewNote] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const urlRef = useRef<string>()

  useEffect(() => {
    listScannerUnits().then(setScanners).catch(() => {})
  }, [])

  const pickFile = (f?: File) => {
    if (!f) return
    if (urlRef.current) URL.revokeObjectURL(urlRef.current)
    const url = URL.createObjectURL(f)
    urlRef.current = url
    setFile(f)
    setPreviewUrl(url)
    setResult(undefined)
    setErr(undefined)
    setReviewed(false)
  }

  const run = async () => {
    if (!file) return
    setBusy(true)
    setErr(undefined)
    setResult(undefined)
    try {
      const selectedUnit = scanners.find(u => String(u.id) === scannerId)
      const res = await runInspection(
        {
          industry: selectedUnit?.industry || 'General',
          product: selectedUnit?.product_name || file.name,
          pipelineId: selectedUnit?.name || 'default',
          scannerUnitId: scannerId ? Number(scannerId) : null,
          threshold,
          fileName: file.name,
        },
        file,
      )
      setResult(res)
    } catch {
      setErr('Sample test failed. Check that the backend is running and try again.')
    } finally {
      setBusy(false)
    }
  }

  const submitReview = async () => {
    if (!result?.inspectionId || !reviewNote.trim()) return
    setReviewing(true)
    try {
      await reviewInspection(result.inspectionId, reviewDecision, reviewNote, feedbackCat)
      setReviewed(true)
      setReviewOpen(false)
    } catch {
      setErr('Review submission failed.')
    } finally {
      setReviewing(false)
    }
  }

  const apiRoot = ((import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1').replace('/api/v1', '')
  const heatmapSrc = result?.heatmap_url ? `${apiRoot}${result.heatmap_url}` : undefined

  return (
    <div className="space-y-5">
      <div className="page-header">
        <div className="flex items-center gap-2">
          <h1>Test Sample</h1>
          <PageHelpLegend
            title="Test Sample"
            summary="Upload a single sample image and test it against a Scanner Unit or the active model."
            items={[
              { label: 'Completed', badge: 'Completed', description: 'Sample passed below the anomaly threshold.' },
              { label: 'Needs review', badge: 'Needs review', description: 'Borderline anomaly score; routed to Review Queue.' },
              { label: 'Failed', badge: 'Failed', description: 'High anomaly score or defect detected above fail threshold.' },
              { label: 'Severity', badge: 'Critical', description: 'Informational / Minor / Major / Critical based on anomaly score.' },
            ]}
          />
        </div>
        <p>Upload a sample image and test it against a Scanner Unit or the active trained model.</p>
      </div>

      <div className="card px-4 py-3 bg-blue-500/10 border-blue-500/30">
        <div className="flex items-start gap-2">
          <AlertCircle size={16} className="text-blue-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-blue-400">
            <strong>Inference engine:</strong> Uses the selected Scanner Unit&apos;s module (or trained <em>EfficientAD-Small</em> when available), falling back to OpenCV contrast heuristic if no trained checkpoint exists.
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        <section className="card p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium">Scanner Unit
              <select className={FIELD} value={scannerId} onChange={e => setScannerId(e.target.value)}>
                <option value="">Default active model</option>
                {scanners.map(s => (
                  <option key={s.id} value={s.id}>{s.name} ({s.status})</option>
                ))}
              </select>
            </label>
            {scanners.length === 0 && (
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                No Scanner Units created yet. <Link to="/scanners" className="text-blue-500 hover:underline">Create one →</Link>
              </p>
            )}
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
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>Higher = less sensitive to anomalies</p>
          </div>

          <label className="flex cursor-pointer flex-col items-center rounded-md border-2 border-dashed p-5 text-sm input-field hover:border-blue-400 transition-colors">
            <Upload size={22} />
            <span className="mt-1 font-medium">{file ? file.name : 'Choose a sample image'}</span>
            <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              {file ? `${(file.size / 1024).toFixed(0)} KB` : 'JPG, PNG up to 50 MB'}
            </span>
            <input type="file" accept="image/*" className="sr-only" onChange={e => pickFile(e.target.files?.[0])} />
          </label>

          <Button className="w-full justify-center" disabled={!file || busy} loading={busy} onClick={run}>
            <Play size={15} />
            {busy ? 'Testing…' : 'Run test sample'}
          </Button>
        </section>

        <section className="card p-4">
          {!previewUrl && !result && (
            <div className="flex flex-col items-center justify-center py-20" style={{ color: 'var(--color-text-secondary)' }}>
              <Upload size={32} className="mb-2" />
              <p className="font-medium">No sample selected</p>
              <p className="text-sm">Upload an image and run a test sample to see results here.</p>
            </div>
          )}

          {err && <ErrorState message={err} onRetry={run} />}

          {previewUrl && (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <figure>
                  <img src={previewUrl} alt="Original sample image" className="aspect-video w-full rounded-md popup-subtle object-contain" />
                  <figcaption className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>Original</figcaption>
                </figure>
                <figure>
                  <div className="relative aspect-video overflow-hidden rounded-md popup-subtle">
                    <img src={heatmapSrc ?? previewUrl} alt="Sample overlay view" className="h-full w-full object-contain" />
                    {result?.defects.map((d, i) => (
                      <div key={i}>
                        <div className="absolute border-2 border-red-500" style={{
                          left: `${d.box.x}%`, top: `${d.box.y}%`,
                          width: `${d.box.w}%`, height: `${d.box.h}%`,
                        }}>
                          <span className="absolute -top-5 left-0 text-xs bg-red-600 text-white px-1 rounded whitespace-nowrap">
                            {d.severity}
                          </span>
                        </div>
                      </div>
                    ))}
                    {busy && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                        <div className="text-sm text-white animate-pulse">Testing sample…</div>
                      </div>
                    )}
                  </div>
                  <figcaption className="mt-1 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                    {result ? `Overlay (${result.model_used ?? 'Inference'})` : 'Overlay will appear after test'}
                  </figcaption>
                </figure>
              </div>

              {result && (
                <div className="space-y-3 border-t pt-3" style={{ borderColor: 'var(--color-border)' }}>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-3xl font-semibold tabular-nums">{result.quality_score}</span>
                    <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>quality score</span>
                    <StatusBadge value={result.status} size="md" />
                    <StatusBadge value={result.severity} size="md" />
                    {result.model_used && (
                      <span className="text-xs px-2 py-0.5 rounded popup-subtle border" style={{ borderColor: 'var(--color-border)' }}>
                        {result.model_used}
                      </span>
                    )}
                    {result.inspectionId && (
                      <Link to={`/inspections/${result.inspectionId}`} className="ml-auto text-xs text-blue-500 hover:underline">
                        View full detail →
                      </Link>
                    )}
                  </div>

                  {result.defects.length > 0 ? (
                    <table>
                      <thead><tr><th>Defect type</th><th>Severity</th><th>Confidence</th><th>Anomaly score</th></tr></thead>
                      <tbody>
                        {result.defects.map((d, i) => (
                          <tr key={i}>
                            <td>{d.type}</td>
                            <td><StatusBadge value={d.severity} /></td>
                            <td className="tabular-nums">{Math.round(d.confidence * 100)}%</td>
                            <td className="tabular-nums">{d.anomalyScore.toFixed(3)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                      No significant anomalies detected above {threshold.toFixed(2)} threshold.
                    </p>
                  )}

                  {reviewed ? (
                    <p className="flex items-center gap-2 text-sm text-green-500">
                      <CheckCircle2 size={16} /> Review & correction feedback recorded.
                    </p>
                  ) : (
                    <Button variant="secondary" onClick={() => setReviewOpen(true)}>
                      Submit human review / feedback
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      <Modal
        open={reviewOpen}
        title="Human Review & Feedback"
        confirmLabel="Submit review"
        onCancel={() => setReviewOpen(false)}
        onConfirm={submitReview}
        confirmDisabled={!reviewNote.trim()}
        confirmLoading={reviewing}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium">Decision</label>
            <div className="mt-1 flex gap-3">
              {(['Approved', 'Rejected'] as const).map(d => (
                <label key={d} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input type="radio" name="decision" value={d} checked={reviewDecision === d}
                    onChange={() => setReviewDecision(d)} className="accent-blue-600" />
                  {d}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium">
              Feedback category
              <select className={FIELD} value={feedbackCat} onChange={e => setFeedbackCat(e.target.value)}>
                {FEEDBACK_CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </label>
            {feedbackCat === 'False positive' && (
              <p className="text-xs text-amber-500 mt-1">
                Image will be copied to <code>data/false_positives/</code> for future review.
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium">
              Review note <span className="text-red-500">*</span>
            </label>
            <textarea
              className={FIELD}
              rows={3} placeholder="Reason for decision…" value={reviewNote}
              onChange={e => setReviewNote(e.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
