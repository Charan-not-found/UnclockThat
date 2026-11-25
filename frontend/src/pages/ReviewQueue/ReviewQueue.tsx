/**
 * Review Queue — dedicated page for inspections requiring human review.
 * Ordered by severity then age. No filter hacks.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { getReviewQueue } from '../../services/inspectionService'
import type { InspectionListItem } from '../../types'

export default function ReviewQueue() {
  const [rows, setRows] = useState<InspectionListItem[]>()
  const [err, setErr] = useState(false)

  const load = () => {
    setErr(false)
    setRows(undefined)
    getReviewQueue(100).then(setRows).catch(() => setErr(true))
  }

  useEffect(load, [])

  if (!rows && !err) return <LoadingState message="Loading review queue…" />
  if (err) return <ErrorState message="Failed to load review queue" onRetry={load} />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div>
          <h1>Review Queue</h1>
          <p>{rows?.length ?? 0} inspection{rows?.length !== 1 ? 's' : ''} awaiting human review · ordered by severity then age</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {rows?.length === 0 ? (
        <div className="card">
          <EmptyState
            title="Queue is empty"
            body="No inspections currently require human review. Great work!"
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

      <div className="card px-4 py-3 bg-amber-50 border-amber-200">
        <div className="flex items-start gap-2">
          <AlertTriangle size={16} className="text-amber-600 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-800">
            Review decisions are recorded with a mandatory note. All reviewed inspections are audited in the database.
          </p>
        </div>
      </div>
    </div>
  )
}
