/**
 * New Inspection page — real file upload → real API → persist result.
 * No mock data. Progress bar only shown while request is in-flight.
 */
import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { Upload, Play, CheckCircle2, AlertCircle } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { ErrorState } from '../../components/common/LoadingState'
import { runInspection, reviewInspection } from '../../services/inspectionService'
import type { InspectionRunResult } from '../../types'

const FIELD = 'mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

const INDUSTRIES: Record<string, string[]> = {
  Automotive:    ['Brake disc', 'Gear housing', 'Engine casing', 'Wheel hub'],
  Electronics:   ['PCB', 'Connector', 'Display panel', 'IC package'],
  Textile:       ['Woven fabric', 'Composite mesh'],
  Aerospace:     ['Turbine blade', 'Structural panel'],
  Manufacturing: ['Generic part'],
}

export default function Inspection() {
  const [industry, setIndustry] = useState('Automotive')
  const [product, setProduct] = useState(INDUSTRIES.Automotive[0])
  const [threshold, setThreshold] = useState(0.5)
  const [file, setFile] = useState<File>()
  const [previewUrl, setPreviewUrl] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<InspectionRunResult>()
  const [err, setErr] = useState<string>()
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewDecision, setReviewDecision] = useState<'Approved' | 'Rejected'>('Approved')
  const [reviewNote, setReviewNote] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const urlRef = useRef<string>()

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
      const res = await runInspection(
        { industry, product, pipelineId: 'default', threshold, fileName: file.name },
        file,
      )
      setResult(res)
    } catch {
      setErr('Inspection failed. Check that the backend is running and try again.')
    } finally {
      setBusy(false)
    }
  }

  const submitReview = async () => {
    if (!result?.inspectionId || !reviewNote.trim()) return
    setReviewing(true)
    try {
      await reviewInspection(result.inspectionId, reviewDecision, reviewNote)
      setReviewed(true)
      setReviewOpen(false)
    } catch {
      setErr('Review submission failed.')
    } finally {
      setReviewing(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1>New Inspection</h1>
        <p>Upload an image and run the prototype inspection pipeline.</p>
      </div>

      {/* Inference engine info */}
      <div className="card px-4 py-3 bg-blue-50 border-blue-200">
        <div className="flex items-start gap-2">
          <AlertCircle size={16} className="text-blue-600 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-blue-800">
            <strong>Inference engine:</strong> Uses the trained <em>EfficientAD-Small</em> model when its checkpoint is
            available, or falls back to the OpenCV heuristic otherwise.
          </p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[300px_1fr]">
        {/* Config panel */}
        <section className="card p-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700">Industry
              <select className={FIELD} value={industry} onChange={e => { setIndustry(e.target.value); setProduct(INDUSTRIES[e.target.value][0]) }}>
                {Object.keys(INDUSTRIES).map(i => <option key={i}>{i}</option>)}
              </select>
            </label>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Product
              <select className={FIELD} value={product} onChange={e => setProduct(e.target.value)}>
                {INDUSTRIES[industry].map(p => <option key={p}>{p}</option>)}
              </select>
            </label>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Anomaly threshold: <span className="font-mono">{threshold.toFixed(2)}</span>
              <input
                type="range" min={0} max={1} step={0.05} value={threshold}
                onChange={e => setThreshold(+e.target.value)}
                className="mt-1 w-full accent-blue-600"
              />
            </label>
            <p className="text-xs text-slate-400 mt-0.5">Higher = less sensitive to anomalies</p>
          </div>

          {/* File upload */}
          <label className="flex cursor-pointer flex-col items-center rounded-md border-2 border-dashed border-slate-300 p-5 text-sm text-slate-500 hover:border-blue-400 hover:bg-blue-50 transition-colors">
            <Upload size={22} className="text-slate-400" />
            <span className="mt-1 font-medium text-slate-600">{file ? file.name : 'Choose an image'}</span>
            <span className="text-xs">{file ? `${(file.size / 1024).toFixed(0)} KB` : 'JPG, PNG up to 50 MB'}</span>
            <input type="file" accept="image/*" className="sr-only" onChange={e => pickFile(e.target.files?.[0])} />
          </label>

          <Button className="w-full justify-center" disabled={!file || busy} loading={busy} onClick={run}>
            <Play size={15} />
            {busy ? 'Analysing…' : 'Run inspection'}
          </Button>
        </section>

        {/* Results panel */}
        <section className="card p-4">
          {!previewUrl && !result && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <Upload size={32} className="mb-2" />
              <p className="font-medium text-slate-600">No image selected</p>
              <p className="text-sm">Upload an image and run an inspection to see results here.</p>
            </div>
          )}

          {err && <ErrorState message={err} onRetry={run} />}

          {previewUrl && (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <figure>
                  <img src={previewUrl} alt="Original uploaded image" className="aspect-video w-full rounded-md bg-slate-100 object-contain" />
                  <figcaption className="mt-1 text-xs text-slate-400">Original</figcaption>
                </figure>
                <figure>
                  <div className="relative aspect-video overflow-hidden rounded-md bg-slate-100">
                    <img src={previewUrl} alt="Inspection overlay view" className="h-full w-full object-contain" />
                    {result?.defects.map((d, i) => (
                      <div key={i}>
                        <div className="absolute rounded-full" style={{
                          left: `${d.box.x - 4}%`, top: `${d.box.y - 4}%`,
                          width: `${d.box.w + 8}%`, height: `${d.box.h + 8}%`,
                          background: 'radial-gradient(circle,rgba(220,38,38,.4),transparent 70%)',
                        }} />
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
                      <div className="absolute inset-0 flex items-center justify-center bg-white/60">
                        <div className="text-sm text-slate-600 animate-pulse">Analysing…</div>
                      </div>
                    )}
                  </div>
                  <figcaption className="mt-1 text-xs text-slate-400">
                    {result ? 'Anomaly localisation overlay (OpenCV heuristic)' : 'Overlay will appear after inspection'}
                  </figcaption>
                </figure>
              </div>

              {result && (
                <div className="space-y-3 border-t border-slate-200 pt-3">
                  {/* Decision header */}
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-3xl font-semibold tabular-nums">{result.quality_score}</span>
                    <span className="text-sm text-slate-400">quality score</span>
                    <StatusBadge value={result.status} size="md" />
                    <StatusBadge value={result.severity} size="md" />
                    {result.inspectionId && (
                      <Link to={`/inspections/${result.inspectionId}`} className="ml-auto text-xs text-blue-600 hover:underline">
                        View full detail →
                      </Link>
                    )}
                  </div>

                  {/* Defect table */}
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
                    <p className="text-sm text-slate-400">No significant anomalies detected above {threshold.toFixed(2)} threshold.</p>
                  )}

                  {/* Review section */}
                  {reviewed ? (
                    <p className="flex items-center gap-2 text-sm text-green-700">
                      <CheckCircle2 size={16} /> Result reviewed and recorded.
                    </p>
                  ) : (
                    <Button variant="secondary" onClick={() => setReviewOpen(true)}>
                      Submit human review
                    </Button>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {/* Review modal */}
      <Modal
        open={reviewOpen}
        title="Human Review"
        confirmLabel="Submit review"
        onCancel={() => setReviewOpen(false)}
        onConfirm={submitReview}
        confirmDisabled={!reviewNote.trim()}
        confirmLoading={reviewing}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Decision</label>
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
            <label className="block text-sm font-medium text-slate-700">
              Review note <span className="text-red-500">*</span>
            </label>
            <textarea
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              rows={3} placeholder="Reason for decision…" value={reviewNote}
              onChange={e => setReviewNote(e.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
