/**
 * Dashboard — Overview page.
 * All metrics computed from real persisted inspections + analytics API.
 * No mock data imported. If no data exists, shows clear empty state.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle, CheckCircle, Clock } from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  PieChart, Pie, Cell,
} from 'recharts'

import StatCard from '../../components/common/StatCard'
import StatusBadge from '../../components/common/StatusBadge'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import Button from '../../components/common/Button'
import { listInspections } from '../../services/inspectionService'
import { getSummary, getTrend, getSeverityDistribution } from '../../services/analyticsService'
import type { InspectionListItem, AnalyticsSummary, DailyPoint, SeverityCount } from '../../types'

const SEV_COLORS: Record<string, string> = {
  Critical: '#dc2626', Major: '#d97706', Minor: '#ca8a04', Informational: '#6b7280',
}

export default function Dashboard() {
  const [rows, setRows] = useState<InspectionListItem[]>()
  const [summary, setSummary] = useState<AnalyticsSummary>()
  const [trend, setTrend] = useState<DailyPoint[]>()
  const [sevDist, setSevDist] = useState<SeverityCount[]>()
  const [err, setErr] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setErr(false)
    setLoading(true)
    Promise.all([
      listInspections({ limit: 20 }),
      getSummary(30),
      getTrend(7),
      getSeverityDistribution(30),
    ])
      .then(([r, s, t, sd]) => { setRows(r); setSummary(s); setTrend(t); setSevDist(sd) })
      .catch(() => setErr(true))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  if (loading) return <LoadingState message="Loading dashboard…" />
  if (err) return <ErrorState message="Couldn't load dashboard data" detail="Check that the backend is running on port 8000." onRetry={load} />

  const total = summary?.total_inspections ?? 0
  const passRate = summary?.pass_rate_pct
  const anomalyRate = summary?.anomaly_rate_pct
  const reviewCount = summary?.review_count ?? 0

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between page-header">
        <div>
          <h1>Overview</h1>
          <p>Live metrics from {total} persisted inspection record{total !== 1 ? 's' : ''} · last 30 days</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard label="Total Inspections" value={total} icon={<CheckCircle size={18} />} />
        <StatCard
          label="Pass Rate (30d)"
          value={passRate != null ? `${passRate}%` : '—'}
          hint={total === 0 ? 'No inspections yet' : `${summary?.pass_count} passed`}
          accent={passRate != null ? (passRate >= 80 ? 'green' : 'red') : 'default'}
        />
        <StatCard
          label="Anomaly Rate (30d)"
          value={anomalyRate != null ? `${anomalyRate}%` : '—'}
          hint={`${summary?.fail_count ?? 0} failed`}
          accent={anomalyRate != null && anomalyRate > 20 ? 'red' : 'default'}
        />
        <StatCard
          label="Awaiting Review"
          value={reviewCount}
          accent={reviewCount > 0 ? 'amber' : 'green'}
          icon={<AlertTriangle size={18} />}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Trend chart */}
        <section className="card p-4 lg:col-span-2">
          <h2 className="mb-1 font-medium text-sm">Inspection trend — last 7 days</h2>
          <p className="mb-3 text-xs text-slate-400">Source: persisted inspection records. Daily counts.</p>
          {trend && trend.some(d => d.inspections > 0) ? (
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={trend} margin={{ left: -10 }}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line name="Inspections" dataKey="inspections" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line name="Anomalies / Fails" dataKey="anomalies" stroke="#dc2626" strokeWidth={2} dot={false} />
                  <Line name="Needs review" dataKey="reviews" stroke="#d97706" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="No inspection data yet" body="Run your first inspection to see trends here." />
          )}
        </section>

        {/* Severity distribution */}
        <section className="card p-4">
          <h2 className="mb-1 font-medium text-sm">Severity distribution (30d)</h2>
          <p className="mb-3 text-xs text-slate-400">From severity_scores table.</p>
          {sevDist && sevDist.length > 0 ? (
            <>
              <div className="h-40">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={sevDist} dataKey="count" nameKey="severity" innerRadius={30} outerRadius={58}>
                      {sevDist.map(d => (
                        <Cell key={d.severity} fill={SEV_COLORS[d.severity] ?? '#94a3b8'} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-1 space-y-1">
                {sevDist.map(d => (
                  <li key={d.severity} className="flex items-center gap-2 text-xs">
                    <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ background: SEV_COLORS[d.severity] ?? '#94a3b8' }} />
                    {d.severity}
                    <span className="ml-auto tabular-nums text-slate-400">{d.count}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <EmptyState title="No severity data" body="Severity distribution appears after inspections." />
          )}
        </section>
      </div>

      {/* Recent inspections table */}
      <section className="card">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
          <h2 className="font-medium text-sm">Recent inspections</h2>
          <Link to="/history" className="text-xs text-blue-600 hover:underline">View all →</Link>
        </div>
        {rows && rows.length > 0 ? (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>ID</th><th>Product</th><th>Industry</th><th>Status</th>
                  <th>Severity</th><th className="tabular-nums">Score</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 8).map(r => (
                  <tr key={r.id}>
                    <td className="font-mono text-xs text-blue-600">
                      <Link to={`/inspections/${r.id}`}>{r.id}</Link>
                    </td>
                    <td className="font-medium">{r.product}</td>
                    <td className="text-slate-500">{r.industry}</td>
                    <td><StatusBadge value={r.status} /></td>
                    <td><StatusBadge value={r.severity} /></td>
                    <td className="tabular-nums">{r.quality_score}</td>
                    <td className="text-slate-400 text-xs">{new Date(r.date).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No inspections yet"
            body="Submit your first inspection to populate this table."
            action={<Link to="/inspect" className="text-sm text-blue-600 hover:underline">Go to New Inspection →</Link>}
          />
        )}
      </section>
    </div>
  )
}
