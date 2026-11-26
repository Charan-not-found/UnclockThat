/**
 * Analytics page — server-computed per Scanner Unit or across all units.
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
  getSummary, getTrend, getSeverityDistribution, getStatusDistribution, getAnalyticsByScannerUnit,
  type ScannerUnitStats,
} from '../../services/analyticsService'
import { listScannerUnits } from '../../services/scannerUnitService'
import type { AnalyticsSummary, DailyPoint, ScannerUnit, SeverityCount, StatusCount } from '../../types'

const SEV_COLORS: Record<string, string> = {
  Critical: '#dc2626', Major: '#d97706', Minor: '#ca8a04', Informational: '#6b7280',
}
const STATUS_COLORS: Record<string, string> = {
  Completed: '#16a34a', Failed: '#dc2626', 'Needs review': '#d97706',
}

export default function Analytics() {
  const [days, setDays] = useState(30)
  const [trendDays, setTrendDays] = useState(14)
  const [scannerId, setScannerId] = useState<string>('')
  const [scanners, setScanners] = useState<ScannerUnit[]>([])
  const [unitStats, setUnitStats] = useState<ScannerUnitStats[]>([])
  const [summary, setSummary] = useState<AnalyticsSummary>()
  const [trend, setTrend] = useState<DailyPoint[]>()
  const [sevDist, setSevDist] = useState<SeverityCount[]>()
  const [statusDist, setStatusDist] = useState<StatusCount[]>()
  const [err, setErr] = useState(false)
  const [loading, setLoading] = useState(true)

  const selectedUnitId = scannerId ? Number(scannerId) : undefined

  const load = () => {
    setErr(false)
    setLoading(true)
    Promise.all([
      listScannerUnits(),
      getSummary(days, selectedUnitId),
      getTrend(trendDays, selectedUnitId),
      getSeverityDistribution(days, selectedUnitId),
      getStatusDistribution(days, selectedUnitId),
      getAnalyticsByScannerUnit(days),
    ])
      .then(([sc, s, t, sd, std, us]) => {
        setScanners(sc)
        setSummary(s)
        setTrend(t)
        setSevDist(sd)
        setStatusDist(std)
        setUnitStats(us)
      })
      .catch(() => setErr(true))
      .finally(() => setLoading(false))
  }

  useEffect(load, [days, trendDays, scannerId])

  if (loading) return <LoadingState message="Loading analytics…" />
  if (err) return <ErrorState message="Failed to load analytics" onRetry={load} />

  const hasData = (summary?.total_inspections ?? 0) > 0

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Analytics</h1>
            <PageHelpLegend
              title="Analytics"
              summary="Server-side aggregated quality trends and defect distributions, filterable per Scanner Unit."
              items={[
                { label: 'Pass Rate', description: 'PASS decisions divided by total inspections in the selected range.' },
                { label: 'Anomaly Rate', description: '(FAIL + Needs review) divided by total inspections in range.' },
              ]}
            />
          </div>
          <p>Server-computed metrics per Scanner Unit from persisted inspection records.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Scanner Unit:
            <select
              className="ml-1 rounded px-2 py-1 text-xs input-field"
              value={scannerId}
              onChange={e => setScannerId(e.target.value)}
            >
              <option value="">All Scanner Units</option>
              {scanners.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </label>
          <label className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Date range:
            <select
              className="ml-1 rounded px-2 py-1 text-xs input-field"
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
      <div className="card px-4 py-3 popup-subtle">
        <div className="flex items-start gap-2">
          <Info size={15} className="mt-0.5 flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }} />
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            <strong>Metric definitions:</strong> Pass Rate = PASS decisions ÷ total inspections.
            Anomaly Rate = (FAIL + REVIEW_REQUIRED) ÷ total.
            {selectedUnitId != null && <> Filtered to Scanner Unit ID <strong>{selectedUnitId}</strong>.</>}
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

      {/* Per-Scanner Unit Breakdown Table */}
      <section className="card">
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <h2 className="font-medium text-sm">Breakdown by Scanner Unit ({days}d)</h2>
        </div>
        {unitStats.length === 0 ? (
          <EmptyState title="No Scanner Unit inspection data yet" body="Run Test Sample with a Scanner Unit to populate per-unit analytics." />
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>Scanner Unit</th><th className="tabular-nums">Total</th>
                  <th className="tabular-nums">Passed</th><th className="tabular-nums">Failed</th>
                  <th className="tabular-nums">Needs Review</th><th className="tabular-nums">Pass Rate</th>
                  <th className="tabular-nums">Anomaly Rate</th>
                </tr>
              </thead>
              <tbody>
                {unitStats.map(u => (
                  <tr key={u.scanner_unit_id ?? 'unassigned'}>
                    <td className="font-medium">
                      {u.scanner_unit_id != null ? (
                        <button
                          type="button"
                          onClick={() => setScannerId(String(u.scanner_unit_id))}
                          className="text-blue-500 hover:underline text-left"
                        >
                          {u.scanner_unit_name}
                        </button>
                      ) : u.scanner_unit_name}
                    </td>
                    <td className="tabular-nums">{u.total_inspections}</td>
                    <td className="tabular-nums text-green-600">{u.pass_count}</td>
                    <td className="tabular-nums text-red-600">{u.fail_count}</td>
                    <td className="tabular-nums text-amber-600">{u.review_count}</td>
                    <td className="tabular-nums">{u.pass_rate_pct != null ? `${u.pass_rate_pct}%` : '—'}</td>
                    <td className="tabular-nums">{u.anomaly_rate_pct != null ? `${u.anomaly_rate_pct}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {!hasData ? (
        <div className="card">
          <EmptyState
            title="No inspection data in selected scope"
            body="Run sample tests to populate trend and distribution charts."
          />
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="card p-4 lg:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
              <div>
                <h2 className="font-medium text-sm">Daily trend</h2>
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Source: inspection_records.inspected_at grouped by day.</p>
              </div>
              <label className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                Days:
                <select className="ml-1 rounded px-2 py-1 text-xs input-field"
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

          <section className="card p-4">
            <h2 className="font-medium text-sm mb-1">Severity distribution</h2>
            <p className="text-xs mb-3" style={{ color: 'var(--color-text-secondary)' }}>From severity_scores · {days}d.</p>
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

          <section className="card p-4">
            <h2 className="font-medium text-sm mb-1">Decision distribution</h2>
            <p className="text-xs mb-3" style={{ color: 'var(--color-text-secondary)' }}>From inspection_records.overall_decision · {days}d.</p>
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
