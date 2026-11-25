/**
 * Review Queue — dedicated page for inspections requiring human review,
 * plus operator correction & false-positive feedback log.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { getReviewQueue, listCorrections } from '../../services/inspectionService'
import type { CorrectionRecord, InspectionListItem } from '../../types'

export default function ReviewQueue() {
  const [rows, setRows] = useState<InspectionListItem[]>()
  const [corrections, setCorrections] = useState<CorrectionRecord[]>([])
  const [err, setErr] = useState(false)

  const load = () => {
    setErr(false)
    setRows(undefined)
    Promise.all([getReviewQueue(100), listCorrections(50)])
      .then(([r, c]) => { setRows(r); setCorrections(c) })
      .catch(() => setErr(true))
  }

  useEffect(load, [])

  if (!rows && !err) return <LoadingState message="Loading review queue…" />
  if (err) return <ErrorState message="Failed to load review queue" onRetry={load} />

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Review Queue</h1>
            <PageHelpLegend
              title="Review Queue"
              summary="Inspections requiring human review, ordered by severity (Critical first) then age."
              items={[
                { label: 'Needs review', badge: 'Needs review', description: 'Awaiting operator decision (Approved or Rejected).' },
                { label: 'False positive', description: 'Normal sample flagged as anomalous — copied to data/false_positives/.' },
              ]}
            />
          </div>
          <p>{rows?.length ?? 0} inspection{rows?.length !== 1 ? 's' : ''} awaiting human review · ordered by severity then age</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {rows?.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Queue is empty"
            body="No inspections currently require human review."
            action={<Link to="/history" className="text-sm text-blue-600">View inspection history →</Link>}
          />
        </div>
      ) : (
        <section className="card">
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>ID</th><th>Product</th><th>Industry</th><th>Station</th>
                  <th>Severity</th><th>Score</th><th>Defects</th><th>Age</th><th>Action</th>
                </tr>
              </thead>
              <tbody>
                {rows?.map(r => {
                  const ageMs = Date.now() - new Date(r.date).getTime()
                  const ageH = Math.floor(ageMs / 3_600_000)
                  const ageLabel = ageH < 1 ? '< 1h ago' : ageH < 24 ? `${ageH}h ago` : `${Math.floor(ageH / 24)}d ago`
                  return (
                    <tr key={r.id}>
                      <td className="font-mono text-xs text-blue-600">
                        <Link to={`/inspections/${r.id}`}>{r.id}</Link>
                      </td>
                      <td className="font-medium">{r.product}</td>
                      <td className="text-slate-500">{r.industry}</td>
                      <td className="text-slate-500">{r.station}</td>
                      <td><StatusBadge value={r.severity} /></td>
                      <td className="tabular-nums">{r.quality_score}</td>
                      <td className="tabular-nums">{r.defect_count}</td>
                      <td className="text-xs text-slate-400">{ageLabel}</td>
                      <td>
                        <Link to={`/inspections/${r.id}`} className="text-xs text-blue-600 hover:underline font-medium">
                          Review →
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Operator Corrections & False Positives Log */}
      <section className="card">
        <div className="px-4 py-3 border-b border-slate-200">
          <h2 className="font-medium text-sm">Correction & False-Positive Records ({corrections.length})</h2>
        </div>
        {corrections.length === 0 ? (
          <EmptyState title="No corrections recorded yet" body="Human review feedback and false positives will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Inspection</th><th>Category</th><th>Decision</th><th>Note</th><th>Saved Sample</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {corrections.map(c => (
                  <tr key={c.id}>
                    <td className="font-mono text-xs">
                      <Link to={`/inspections/${c.inspection_id}`} className="text-blue-600 hover:underline">{c.inspection_id}</Link>
                    </td>
                    <td><StatusBadge value={c.feedback_category === 'False positive' ? 'Needs review' : 'Completed'} /> <span className="ml-1 text-xs">{c.feedback_category}</span></td>
                    <td className="text-xs font-medium">{c.corrected_decision}</td>
                    <td className="text-xs text-slate-600 max-w-xs truncate">{c.note}</td>
                    <td className="text-xs font-mono text-slate-400">{c.saved_image_path ?? '—'}</td>
                    <td className="text-xs text-slate-400">{new Date(c.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="card px-4 py-3 bg-amber-50 border-amber-200">
        <div className="flex items-start gap-2">
          <AlertTriangle size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-800">
            False-positive images are saved to <code>data/false_positives/</code> and require review before being incorporated into future training iterations.
          </p>
        </div>
      </div>
    </div>
  )
}
