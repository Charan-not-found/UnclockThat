/**
 * Dashboard — Overview page.
 * Implemented per docs/overview_page.md:
 * - Concurrent fetching via Promise.allSettled with per-section error isolation
 * - Structured skeleton initial loading & non-destructive refresh
 * - 4 KPI cards, Inspection Activity (7d) multi-series chart, Defect Severity Distribution (30d)
 * - Recent Inspections (latest 8) with real persisted data only
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, AlertTriangle, CheckCircle, Activity, ShieldAlert } from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  PieChart, Pie, Cell,
} from 'recharts'

import StatCard from '../../components/common/StatCard'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { ErrorState, EmptyState } from '../../components/common/LoadingState'
import Button from '../../components/common/Button'
import { listInspections } from '../../services/inspectionService'
import { getSummary, getTrend, getSeverityDistribution } from '../../services/analyticsService'
import type { InspectionListItem, AnalyticsSummary, DailyPoint, SeverityCount } from '../../types'

const SEVERITY_ORDER = ['Critical', 'Major', 'Minor', 'Informational'] as const

const SEV_COLORS: Record<string, string> = {
  Critical: '#dc2626',
  Major: '#d97706',
  Minor: '#ca8a04',
  Informational: '#6b7280',
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5 animate-pulse" aria-label="Loading overview dashboard">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-7 w-36 rounded bg-slate-700/30" />
          <div className="h-4 w-72 rounded bg-slate-700/20" />
        </div>
        <div className="h-8 w-24 rounded bg-slate-700/25" />
      </div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="card p-4 space-y-2">
            <div className="h-3 w-24 rounded bg-slate-700/25" />
            <div className="h-7 w-16 rounded bg-slate-700/30" />
            <div className="h-3 w-28 rounded bg-slate-700/20" />
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-4 lg:col-span-2 h-72 bg-slate-700/10" />
        <div className="card p-4 h-72 bg-slate-700/10" />
      </div>
      <div className="card p-4 h-56 bg-slate-700/10" />
    </div>
  )
}

export default function Dashboard() {
  const [rows, setRows] = useState<InspectionListItem[]>()
  const [summary, setSummary] = useState<AnalyticsSummary>()
  const [trend, setTrend] = useState<DailyPoint[]>()
  const [sevDist, setSevDist] = useState<SeverityCount[]>()

  const [summaryErr, setSummaryErr] = useState(false)
  const [trendErr, setTrendErr] = useState(false)
  const [sevErr, setSevErr] = useState(false)
  const [rowsErr, setRowsErr] = useState(false)

  const [initialLoading, setInitialLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [hoveredSeverity, setHoveredSeverity] = useState<string | null>(null)

  const inFlightRef = useRef(false)

  const loadAll = useCallback(async () => {
    if (inFlightRef.current) return
    inFlightRef.current = true
    setRefreshing(true)

    try {
      const [rowsRes, sumRes, trendRes, sevRes] = await Promise.allSettled([
        listInspections({ limit: 20 }),
        getSummary(30),
        getTrend(7),
        getSeverityDistribution(30),
      ])

      let anyOk = false

      if (rowsRes.status === 'fulfilled') {
        setRows(rowsRes.value)
        setRowsErr(false)
        anyOk = true
      } else {
        setRowsErr(true)
      }

      if (sumRes.status === 'fulfilled') {
        setSummary(sumRes.value)
        setSummaryErr(false)
        anyOk = true
      } else {
        setSummaryErr(true)
      }

      if (trendRes.status === 'fulfilled') {
        setTrend(trendRes.value)
        setTrendErr(false)
        anyOk = true
      } else {
        setTrendErr(true)
      }

      if (sevRes.status === 'fulfilled') {
        setSevDist(sevRes.value)
        setSevErr(false)
        anyOk = true
      } else {
        setSevErr(true)
      }

      if (anyOk) {
        setLastUpdated(new Date())
      }
    } finally {
      inFlightRef.current = false
      setInitialLoading(false)
      setRefreshing(false)
    }
  }, [])

  const retrySection = async (section: 'summary' | 'trend' | 'sev' | 'rows') => {
    try {
      if (section === 'summary') {
        const s = await getSummary(30)
        setSummary(s)
        setSummaryErr(false)
      } else if (section === 'trend') {
        const t = await getTrend(7)
        setTrend(t)
        setTrendErr(false)
      } else if (section === 'sev') {
        const sd = await getSeverityDistribution(30)
        setSevDist(sd)
        setSevErr(false)
      } else {
        const r = await listInspections({ limit: 20 })
        setRows(r)
        setRowsErr(false)
      }
      setLastUpdated(new Date())
    } catch {
      // Keep section error visible
    }
  }

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  if (initialLoading) return <DashboardSkeleton />

  const allFailedWithoutData =
    summaryErr && trendErr && sevErr && rowsErr &&
    summary === undefined && trend === undefined && sevDist === undefined && rows === undefined

  if (allFailedWithoutData) {
    return (
      <ErrorState
        message="Couldn't load dashboard data."
        detail="Check that the backend is running on port 8000."
        onRetry={() => void loadAll()}
      />
    )
  }

  const total = summary?.total_inspections ?? 0
  const passRate = summary?.pass_rate_pct
  const anomalyRate = summary?.anomaly_rate_pct
  const reviewCount = summary?.review_count ?? 0

  const updatedLabel = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—'

  // Build ordered severity breakdown list from actual severity_scores counts
  const sevMap = new Map((sevDist ?? []).map(d => [d.severity, d.count]))
  const hasSeverityData = (sevDist ?? []).some(d => d.count > 0)

  return (
    <div className="space-y-5">
      {/* 1. Page Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Overview</h1>
            <PageHelpLegend
              title="Overview"
              summary="Live inspection performance and quality analytics from persisted records."
              items={[
                { label: 'Pass Rate', description: 'Percentage of inspections with a PASS decision.' },
                { label: 'Anomaly Rate', description: 'Percentage of inspections with FAIL or REVIEW_REQUIRED decisions.' },
                { label: 'Critical', badge: 'Critical', description: 'Highest severity classification.' },
                { label: 'Major', badge: 'Major', description: 'Significant defect classification.' },
                { label: 'Minor', badge: 'Minor', description: 'Lower-severity defect classification.' },
                { label: 'Informational', badge: 'Informational', description: 'Non-critical observation.' },
              ]}
            />
          </div>
          <p>Live inspection performance and quality analytics</p>
          <p className="text-xs mt-0.5 tabular-nums" style={{ color: 'var(--color-text-secondary)' }}>
            {summary !== undefined ? `${total} inspection record${total !== 1 ? 's' : ''}` : '— inspection records'}
            {' · '}Last 30 days{' · '}Updated {updatedLabel}
          </p>
        </div>
        <Button variant="ghost" size="sm" disabled={refreshing} onClick={() => void loadAll()}>
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </Button>
      </div>

      {/* 2. KPI Overview */}
      {summaryErr && summary === undefined ? (
        <section className="card p-4">
          <ErrorState
            message="Couldn't load KPI summary."
            detail="Check that the backend is running on port 8000."
            onRetry={() => void retrySection('summary')}
          />
        </section>
      ) : (
        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <Link to="/history" className="block rounded-lg transition-opacity hover:opacity-95">
            <StatCard
              label="Total Inspections"
              value={total}
              hint="Last 30 days"
              icon={<Activity size={18} />}
            />
          </Link>
          <Link to="/history" className="block rounded-lg transition-opacity hover:opacity-95">
            <StatCard
              label="Pass Rate (30d)"
              value={passRate != null ? `${passRate}%` : '—'}
              hint={total === 0 ? 'No inspection records' : `${summary?.pass_count ?? 0} products passed`}
              accent={passRate != null ? (passRate >= 80 ? 'green' : 'red') : 'default'}
              icon={<CheckCircle size={18} />}
            />
          </Link>
          <Link to="/history" className="block rounded-lg transition-opacity hover:opacity-95">
            <StatCard
              label="Anomaly Rate (30d)"
              value={anomalyRate != null ? `${anomalyRate}%` : '—'}
              hint={total === 0 ? 'No inspection records' : `${summary?.fail_count ?? 0} failed`}
              accent={anomalyRate != null && anomalyRate > 20 ? 'red' : 'default'}
              icon={<ShieldAlert size={18} />}
            />
          </Link>
          <Link to="/history" className="block rounded-lg transition-opacity hover:opacity-95">
            <StatCard
              label="Awaiting Review"
              value={reviewCount}
              hint="Inspections requiring operator attention"
              accent={reviewCount > 0 ? 'amber' : 'green'}
              icon={<AlertTriangle size={18} />}
            />
          </Link>
        </div>
      )}

      {/* 3. Inspection Analytics */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* A. Inspection Activity (7d) */}
        <section className="card p-4 lg:col-span-2">
          <h2 className="mb-0.5 font-medium text-sm">Inspection Activity</h2>
          <p className="mb-3 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Daily inspection volume and quality outcomes.
          </p>
          {trendErr && trend === undefined ? (
            <ErrorState
              message="Couldn't load inspection activity trend."
              onRetry={() => void retrySection('trend')}
            />
          ) : trend && trend.some(d => d.inspections > 0) ? (
            <div className="h-56">
              <ResponsiveContainer>
                <LineChart data={trend} margin={{ left: -10, right: 8 }}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Line name="Total Inspections" dataKey="inspections" stroke="#2563eb" strokeWidth={2} dot={false} />
                  <Line name="Failed Inspections" dataKey="anomalies" stroke="#dc2626" strokeWidth={2} dot={false} />
                  <Line name="Needs Review" dataKey="reviews" stroke="#d97706" strokeWidth={1.75} dot={false} strokeDasharray="4 2" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState
              title="No inspection data yet."
              body="Run your first inspection to see activity trends here."
            />
          )}
        </section>

        {/* B. Defect Severity Distribution (30d) */}
        <section className="card p-4">
          <h2 className="mb-0.5 font-medium text-sm">Defect Severity Distribution</h2>
          <p className="mb-3 text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Severity classifications from inspection results.
          </p>
          {sevErr && sevDist === undefined ? (
            <ErrorState
              message="Couldn't load severity distribution."
              onRetry={() => void retrySection('sev')}
            />
          ) : hasSeverityData && sevDist ? (
            <>
              <div className="h-40">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie
                      data={sevDist}
                      dataKey="count"
                      nameKey="severity"
                      innerRadius={32}
                      outerRadius={58}
                      onMouseEnter={(_, idx) => setHoveredSeverity(sevDist[idx]?.severity ?? null)}
                      onMouseLeave={() => setHoveredSeverity(null)}
                    >
                      {sevDist.map(d => (
                        <Cell
                          key={d.severity}
                          fill={SEV_COLORS[d.severity] ?? '#94a3b8'}
                          opacity={hoveredSeverity && hoveredSeverity !== d.severity ? 0.45 : 1}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="mt-2 space-y-1">
                {SEVERITY_ORDER.map(sev => {
                  const count = sevMap.get(sev) ?? 0
                  const active = hoveredSeverity === sev
                  return (
                    <li
                      key={sev}
                      className={`flex items-center gap-2 rounded px-1.5 py-0.5 text-xs transition-colors ${active ? 'bg-slate-500/15 font-semibold' : ''}`}
                    >
                      <span
                        className="h-2 w-2 rounded-full flex-shrink-0"
                        style={{ background: SEV_COLORS[sev] ?? '#94a3b8' }}
                      />
                      <span>{sev}</span>
                      <span className="ml-auto tabular-nums" style={{ color: 'var(--color-text-secondary)' }}>
                        {count}
                      </span>
                    </li>
                  )
                })}
              </ul>
            </>
          ) : (
            <EmptyState
              title="No severity data available."
              body="Severity distribution will appear after inspections generate severity classifications."
            />
          )}
        </section>
      </div>

      {/* 4. Recent Inspections */}
      <section className="card">
        <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--color-border)' }}>
          <h2 className="font-medium text-sm">Recent Inspections</h2>
          <Link to="/history" className="text-xs text-blue-600 hover:underline">View all →</Link>
        </div>
        {rowsErr && rows === undefined ? (
          <div className="p-4">
            <ErrorState
              message="Couldn't load recent inspections."
              onRetry={() => void retrySection('rows')}
            />
          </div>
        ) : rows && rows.length > 0 ? (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Product</th>
                  <th>Industry</th>
                  <th>Status</th>
                  <th>Severity</th>
                  <th className="tabular-nums">Score</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 8).map(r => (
                  <tr key={r.id}>
                    <td className="font-mono text-xs text-blue-600 whitespace-nowrap">
                      <Link to={`/inspections/${r.id}`}>{r.id}</Link>
                    </td>
                    <td className="font-medium max-w-[200px] truncate" title={r.product}>{r.product}</td>
                    <td style={{ color: 'var(--color-text-secondary)' }}>{r.industry}</td>
                    <td><StatusBadge value={r.status} /></td>
                    <td><StatusBadge value={r.severity} /></td>
                    <td className="tabular-nums">{r.quality_score != null ? r.quality_score : '—'}</td>
                    <td className="text-xs whitespace-nowrap" style={{ color: 'var(--color-text-secondary)' }}>
                      {new Date(r.date).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="No inspections yet."
            body="Submit your first test sample to populate your inspection history."
            action={<Link to="/test-sample" className="text-sm text-blue-600 hover:underline">Go to Test Sample →</Link>}
          />
        )}
      </section>
    </div>
  )
}
