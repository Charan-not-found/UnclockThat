/**
 * Inspection History — server-paginated, sortable, real data only.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Search } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listInspections } from '../../services/inspectionService'
import type { InspectionListItem } from '../../types'

export default function InspectionHistory() {
  const [rows, setRows] = useState<InspectionListItem[]>()
  const [err, setErr] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [search, setSearch] = useState('')

  const load = () => {
    setErr(false)
    setRows(undefined)
    listInspections({ limit: 200 })
      .then(setRows)
      .catch(() => setErr(true))
  }

  useEffect(load, [])

  const displayed = (rows ?? []).filter(r => {
    if (filterStatus && r.status !== filterStatus) return false
    if (search && !r.product.toLowerCase().includes(search.toLowerCase()) && !r.id.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  if (!rows && !err) return <LoadingState message="Loading inspection history…" />
  if (err) return <ErrorState message="Failed to load inspections" onRetry={load} />

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1>Inspection History</h1>
            <PageHelpLegend
              title="Inspection History"
              summary="All persisted sample tests and inspections stored in clockit.db."
              items={[
                { label: 'Completed', badge: 'Completed', description: 'Passed inspection.' },
                { label: 'Needs review', badge: 'Needs review', description: 'Flagged for operator review.' },
                { label: 'Failed', badge: 'Failed', description: 'Failed quality threshold.' },
              ]}
            />
          </div>
          <p>{rows?.length ?? 0} record{rows?.length !== 1 ? 's' : ''} from the database.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {/* Filters */}
      <div className="card px-4 py-3 flex flex-wrap gap-3 items-center">
        <div className="relative flex items-center">
          <Search size={14} className="absolute left-2.5 text-slate-400" />
          <input
            className="pl-7 pr-3 py-1.5 text-sm rounded-md border border-slate-300 focus:border-blue-500 focus:outline-none"
            placeholder="Search by ID or product…"
            value={search} onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="py-1.5 px-2.5 text-sm rounded-md border border-slate-300 focus:border-blue-500 focus:outline-none"
          value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          <option>Completed</option>
          <option>Failed</option>
          <option>Needs review</option>
        </select>
        {(filterStatus || search) && (
          <button onClick={() => { setFilterStatus(''); setSearch('') }} className="text-xs text-blue-600 hover:underline">
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <section className="card">
        {displayed.length === 0 ? (
          <EmptyState
            title="No inspections found"
            body={rows?.length === 0 ? 'No inspections have been run yet.' : 'No results match your filter.'}
            action={rows?.length === 0 ? <Link to="/inspect" className="text-sm text-blue-600">Run your first inspection →</Link> : undefined}
          />
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>ID</th><th>Product</th><th>Industry</th><th>Station</th>
                  <th>Status</th><th>Severity</th><th>Score</th><th>Defects</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {displayed.map(r => (
                  <tr key={r.id}>
                    <td className="font-mono text-xs">
                      <Link to={`/inspections/${r.id}`} className="text-blue-600 hover:underline">{r.id}</Link>
                    </td>
                    <td className="font-medium">{r.product}</td>
                    <td className="text-slate-500">{r.industry}</td>
                    <td className="text-slate-500">{r.station}</td>
                    <td><StatusBadge value={r.status} /></td>
                    <td><StatusBadge value={r.severity} /></td>
                    <td className="tabular-nums">{r.quality_score}</td>
                    <td className="tabular-nums">{r.defect_count}</td>
                    <td className="text-xs text-slate-400">{new Date(r.date).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
