/**
 * Analytics page — all metrics server-computed, with definitions and denominators.
 * No fabricated numbers. Empty datasets show "no data" explicitly.
 */
import { useEffect, useState } from 'react'
import { RefreshCw, Info } from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, Legend, Cell, PieChart, Pie,
} from 'recharts'
import Button from '../../components/common/Button'
import StatCard from '../../components/common/StatCard'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import {
  getSummary, getTrend, getSeverityDistribution, getStatusDistribution,
} from '../../services/analyticsService'
import type { AnalyticsSummary, DailyPoint, SeverityCount, StatusCount } from '../../types'

const SEV_COLORS: Record<string, string> = {
  Critical: '#dc2626', Major: '#d97706', Minor: '#ca8a04', Informational: '#6b7280',
}
const STATUS_COLORS: Record<string, string> = {
  Completed: '#16a34a', Failed: '#dc2626', 'Needs review': '#d97706',
}

export default function Analytics() {
  const [days, setDays] = useState(30)
  const [trendDays, setTrendDays] = useState(14)
  const [summary, setSummary] = useState<AnalyticsSummary>()
  const [trend, setTrend] = useState<DailyPoint[]>()
  const [sevDist, setSevDist] = useState<SeverityCount[]>()
  const [statusDist, setStatusDist] = useState<StatusCount[]>()
  const [err, setErr] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = () => {
    setErr(false)
    setLoading(true)
    Promise.all([
      getSummary(days),
      getTrend(trendDays),
      getSeverityDistribution(days),
      getStatusDistribution(days),
    ])
      .then(([s, t, sd, std]) => { setSummary(s); setTrend(t); setSevDist(sd); setStatusDist(std) })
      .catch(() => setErr(true))
      .finally(() => setLoading(false))
  }

  useEffect(load, [days, trendDays])

  if (loading) return <LoadingState message="Loading analytics…" />
  if (err) return <ErrorState message="Failed to load analytics" onRetry={load} />

  const hasData = (summary?.total_inspections ?? 0) > 0

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Analytics</h1>
            <PageHelpLegend
              title="Analytics"
              summary="Server-side aggregated quality trends and defect distributions."
              items={[
                { label: 'Pass Rate', description: 'PASS decisions divided by total inspections in the selected date range.' },
                { label: 'Anomaly Rate', description: '(FAIL + Needs review) divided by total inspections in range.' },
              ]}
            />
          </div>
          <p>All metrics computed server-side from persisted inspection records.</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-slate-500">Date range:
            <select
              className="ml-1 rounded border border-slate-300 px-2 py-1 text-xs"
              value={days} onChange={e => setDays(+e.target.value)}
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
        </div>
      </div>

      {/* Metric definition banner */}
      <div className="card px-4 py-3 bg-slate-50 border-slate-200">
        <div className="flex items-start gap-2">
          <Info size={15} className="text-slate-500 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-slate-500">
            <strong>Metric definitions:</strong> Pass Rate = PASS decisions ÷ total inspections (denominator: all completed inspections in range).
            Anomaly Rate = (FAIL + REVIEW_REQUIRED) ÷ total. All counts from <code className="bg-slate-100 px-1 rounded">inspection_records</code> and <code className="bg-slate-100 px-1 rounded">severity_scores</code> tables.
          </p>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <StatCard label={`Total Inspections (${days}d)`} value={summary?.total_inspections ?? 0} />
        <StatCard
          label={`Pass Rate (${days}d)`}
          value={summary?.pass_rate_pct != null ? `${summary.pass_rate_pct}%` : '—'}
          hint={summary?.total_inspections === 0 ? 'No data yet' : `Denominator: ${summary?.total_inspections} inspections`}
          accent={summary?.pass_rate_pct != null ? (summary.pass_rate_pct >= 80 ? 'green' : 'red') : 'default'}
        />
        <StatCard
          label={`Anomaly Rate (${days}d)`}
          value={summary?.anomaly_rate_pct != null ? `${summary.anomaly_rate_pct}%` : '—'}
          hint="FAIL + Needs review ÷ total"
          accent={summary?.anomaly_rate_pct != null && summary.anomaly_rate_pct > 20 ? 'red' : 'default'}
        />
        <StatCard label={`Needs Review (${days}d)`} value={summary?.review_count ?? 0} accent="amber" />
      </div>

      {!hasData ? (
        <div className="card">
          <EmptyState
            title="No inspection data in selected range"
            body="Run inspections to populate analytics. Empty datasets do not produce rates or percentages."
          />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {/* Trend */}
          <section className="card p-4 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
              <div>
                <h2 className="font-medium text-sm">Daily trend</h2>
                <p className="text-xs text-slate-400">Source: inspection_records.inspected_at grouped by day.</p>
              </div>
              <label className="text-xs text-slate-500">Days:
                <select className="ml-1 rounded border border-slate-300 px-2 py-1 text-xs"
                  value={trendDays} onChange={e => setTrendDays(+e.target.value)}>
                  <option value={7}>7</option>
                  <option value={14}>14</option>
                  <option value={30}>30</option>
                </select>
              </label>
            </div>
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={trend ?? []} margin={{ left: -10 }}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line name="Inspections" dataKey="inspections" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line name="Anomalies" dataKey="anomalies" stroke="#dc2626" strokeWidth={1.5} dot={false} />
                  <Line name="Needs review" dataKey="reviews" stroke="#d97706" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Severity distribution */}
          <section className="card p-4">
            <h2 className="font-medium text-sm mb-1">Severity distribution</h2>
            <p className="text-xs text-slate-400 mb-3">From severity_scores table · {days}d · count per label.</p>
            {sevDist && sevDist.length > 0 ? (
              <div className="h-48">
                <ResponsiveContainer>
                  <BarChart data={sevDist} margin={{ left: -20 }}>
                    <XAxis dataKey="severity" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                      {sevDist.map(d => (
                        <Cell key={d.severity} fill={SEV_COLORS[d.severity] ?? '#94a3b8'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="No severity data" body="Appears after inspections with anomalies." />
            )}
          </section>

          {/* Status distribution */}
          <section className="card p-4">
            <h2 className="font-medium text-sm mb-1">Decision distribution</h2>
            <p className="text-xs text-slate-400 mb-3">From inspection_records.overall_decision · {days}d.</p>
            {statusDist && statusDist.length > 0 ? (
              <div className="h-48">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={statusDist} dataKey="count" nameKey="status" innerRadius={35} outerRadius={65} label={d => `${d.status}: ${d.count}`} labelLine={false}>
                      {statusDist.map(d => (
                        <Cell key={d.status} fill={STATUS_COLORS[d.status] ?? '#94a3b8'} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="No decision data" />
            )}
          </section>
        </div>
      )}
    </div>
  )
}
