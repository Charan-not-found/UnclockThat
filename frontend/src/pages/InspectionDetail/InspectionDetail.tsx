/**
 * Inspection Detail page — full evidence viewer with anomaly results,
 * per-stage model outputs, human review panel.
 */
import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Eye, EyeOff, CheckCircle2 } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { LoadingState, ErrorState } from '../../components/common/LoadingState'
import { getInspection, reviewInspection } from '../../services/inspectionService'
import type { InspectionDetail } from '../../types'

export default function InspectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<InspectionDetail>()
  const [err, setErr] = useState(false)
  const [showOverlay, setShowOverlay] = useState(true)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewDecision, setReviewDecision] = useState<'Approved' | 'Rejected'>('Approved')
  const [feedbackCat, setFeedbackCat] = useState('Correct detection')
  const [reviewNote, setReviewNote] = useState('')
  const [reviewing, setReviewing] = useState(false)
  const [reviewed, setReviewed] = useState(false)

  useEffect(() => {
    if (!id) return
    setErr(false)
    setDetail(undefined)
    getInspection(id)
      .then(d => { setDetail(d); setReviewed(!d.requires_review) })
      .catch(() => setErr(true))
  }, [id])

  const submitReview = async () => {
    if (!detail || !reviewNote.trim()) return
    setReviewing(true)
    try {
      await reviewInspection(detail.id, reviewDecision, reviewNote, feedbackCat)
      setReviewed(true)
      setReviewOpen(false)
      // Refresh
      const updated = await getInspection(id!)
      setDetail(updated)
    } catch {
      // keep modal open
    } finally {
      setReviewing(false)
    }
  }

  if (!detail && !err) return <LoadingState message="Loading inspection detail…" />
  if (err || !detail) return <ErrorState message="Inspection not found or could not be loaded." />

  const hasAnomalyResults = detail.anomaly_results.length > 0
  const topResult = hasAnomalyResults ? detail.anomaly_results[0] : null

  return (
    <div className="space-y-5">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Link to="/history" className="text-sm text-blue-600 hover:underline flex items-center gap-1">
          <ArrowLeft size={14} /> Inspection History
        </Link>
        <span className="text-slate-300">/</span>
        <span className="font-mono text-sm">{detail.id}</span>
      </div>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{detail.id}</h1>
          <p className="text-sm text-slate-500">
            {detail.product} · {detail.industry} · {detail.station} · {detail.pipeline}
          </p>
          <p className="text-xs text-slate-400 mt-0.5">{new Date(detail.date).toLocaleString()}</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge value={detail.status} size="md" />
          <StatusBadge value={detail.severity} size="md" />
          <span className="text-2xl font-semibold tabular-nums text-slate-800">{detail.quality_score}</span>
          <span className="text-xs text-slate-400">score</span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        {/* Evidence viewer */}
        <div className="space-y-3">
          <section className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-sm">Evidence viewer</h2>
              <button
                onClick={() => setShowOverlay(o => !o)}
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-800"
                aria-pressed={showOverlay}
              >
                {showOverlay ? <EyeOff size={14} /> : <Eye size={14} />}
                {showOverlay ? 'Hide overlays' : 'Show overlays'}
              </button>
            </div>

            <div className="relative overflow-hidden rounded-md bg-slate-100 aspect-video">
              {/* We serve the uploaded image via storage/ path — in dev the backend serves it */}
              {/* Try to serve the uploaded image via /uploads/<filename> static route */}
              {(() => {
                const filename = detail.image_path.split(/[\\/]/).pop()
                const API = (import.meta.env.VITE_API_URL as string | undefined)?.replace('/api/v1', '') ?? 'http://localhost:8000'
                const imgUrl = filename ? `${API}/uploads/${filename}` : null
                return imgUrl ? (
                  <img
                    src={imgUrl}
                    alt={`Inspection evidence for ${detail.id}`}
                    className="h-full w-full object-contain"
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none' }}
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-400 text-sm">
                    <p>Image path unavailable</p>
                  </div>
                )
              })()}

              {/* Defect overlays */}
              {showOverlay && topResult && topResult.defects.map((d, i) => (
                <div key={i}>
                  <div className="absolute border-2 border-red-500 rounded" style={{
                    left: `${d.box.x}%`, top: `${d.box.y}%`,
                    width: `${d.box.w}%`, height: `${d.box.h}%`,
                  }}>
                    <span className="absolute -top-5 left-0 text-xs bg-red-600 text-white px-1 rounded whitespace-nowrap">
                      {d.severity} · {Math.round(d.confidence * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <p className="mt-1 text-xs text-slate-400">
              Overlay source: OpenCV heuristic bounding boxes stored in anomaly_results table.
              {!showOverlay && ' Overlays hidden.'}
            </p>
          </section>

          {/* Per-stage anomaly results */}
          <section className="card p-4">
            <h2 className="font-medium text-sm mb-3">Model stage results</h2>
            {hasAnomalyResults ? (
              <div className="space-y-3">
                {detail.anomaly_results.map(ar => (
                  <div key={ar.id} className="border border-slate-200 rounded-md p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <p className="font-medium text-sm">{ar.model_name}</p>
                        <p className="text-xs text-slate-400 mt-0.5">Stage ID: {ar.id}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge value={ar.severity} />
                        <span className={`text-xs font-medium ${ar.is_anomalous ? 'text-red-600' : 'text-green-600'}`}>
                          {ar.is_anomalous ? 'Anomalous' : 'Normal'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs text-slate-500">
                      <div><span className="text-slate-400">Anomaly score</span><br />
                        <span className="font-mono font-medium text-slate-800">{ar.anomaly_score.toFixed(4)}</span>
                      </div>
                      <div><span className="text-slate-400">Confidence</span><br />
                        <span className="font-mono font-medium text-slate-800">{(ar.confidence_score * 100).toFixed(1)}%</span>
                      </div>
                      <div><span className="text-slate-400">Processing</span><br />
                        <span className="font-mono font-medium text-slate-800">
                          {ar.processing_time_ms != null ? `${ar.processing_time_ms.toFixed(0)} ms` : '—'}
                        </span>
                      </div>
                    </div>

                    {ar.defects.length > 0 && (
                      <table className="mt-2 text-xs">
                        <thead><tr><th>Type</th><th>Severity</th><th>Confidence</th><th>Anomaly score</th></tr></thead>
                        <tbody>
                          {ar.defects.map((d, i) => (
                            <tr key={i}>
                              <td>{d.type}</td>
                              <td><StatusBadge value={d.severity} size="sm" /></td>
                              <td className="tabular-nums">{Math.round(d.confidence * 100)}%</td>
                              <td className="tabular-nums">{d.anomalyScore.toFixed(3)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">No anomaly results recorded for this inspection.</p>
            )}
          </section>
        </div>

        {/* Right panel: evidence provenance + review */}
        <div className="space-y-3">
          {/* Evidence provenance */}
          <section className="card p-4">
            <h2 className="font-medium text-sm mb-3">Evidence provenance</h2>
            <dl className="space-y-2 text-xs">
              {[
                ['Pipeline', detail.pipeline],
                ['Pipeline ID', detail.pipeline_id ?? '—'],
                ['Overall decision', detail.overall_decision],
                ['Image path', detail.image_path],
              ].map(([k, v]) => (
                <div key={k} className="flex flex-col gap-0.5">
                  <dt className="text-slate-400">{k}</dt>
                  <dd className="font-medium text-slate-700 break-all">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-3 text-xs text-slate-400">
              Model artifact hash and pipeline version tracking are planned for future milestones.
            </p>
          </section>

          {/* Human review */}
          <section className="card p-4">
            <h2 className="font-medium text-sm mb-3">Human review</h2>
            {reviewed || !detail.requires_review ? (
              <div className="space-y-2">
                <p className="flex items-center gap-2 text-sm text-green-700">
                  <CheckCircle2 size={16} /> {reviewed ? 'Review submitted.' : 'No review required.'}
                </p>
                {detail.review_note && (
                  <div className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
                    {detail.review_note}
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-amber-700 bg-amber-50 rounded-md px-3 py-2">
                  This inspection requires human review before it can be acted upon.
                </p>
                <Button variant="secondary" size="sm" className="w-full justify-center" onClick={() => setReviewOpen(true)}>
                  Submit review decision
                </Button>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Review modal */}
      <Modal
        open={reviewOpen}
        title="Submit Review Decision"
        confirmLabel="Submit review"
        onCancel={() => setReviewOpen(false)}
        onConfirm={submitReview}
        confirmDisabled={!reviewNote.trim()}
        confirmLoading={reviewing}
      >
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Inspection: <strong>{detail.id}</strong> · Product: {detail.product}
          </p>
          <div>
            <label className="block text-sm font-medium text-slate-700">Decision</label>
            <div className="mt-1 flex gap-4">
              {(['Approved', 'Rejected'] as const).map(d => (
                <label key={d} className="flex items-center gap-2 cursor-pointer text-sm">
                  <input type="radio" name="dec" value={d} checked={reviewDecision === d}
                    onChange={() => setReviewDecision(d)} className="accent-blue-600" />
                  {d}
                </label>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Feedback category
              <select
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                value={feedbackCat}
                onChange={e => setFeedbackCat(e.target.value)}
              >
                {['Correct detection', 'False positive', 'False negative', 'Incorrect localization', 'Incorrect class', 'Uncertain'].map(c => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">
              Review note <span className="text-red-500">*</span>
            </label>
            <textarea
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              rows={3} placeholder="Required: reason for this decision…"
              value={reviewNote} onChange={e => setReviewNote(e.target.value)}
            />
          </div>
        </div>
      </Modal>
    </div>
  )
}
