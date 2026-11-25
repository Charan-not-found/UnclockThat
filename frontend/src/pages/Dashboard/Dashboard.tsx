import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, PieChart, Pie, Cell } from 'recharts'
import StatCard from '../../components/common/StatCard'
import StatusBadge from '../../components/common/StatusBadge'
import { LoadingState, ErrorState } from '../../components/common/LoadingState'
import { listInspections } from '../../services/inspectionService'
import { trend, distribution, models } from '../../services/mockData'
import type { Inspection } from '../../types'
const colors = ['#2563eb','#dc2626','#d97706','#16a34a']
export default function Dashboard() {
 const [rows, setRows] = useState<Inspection[]>(); const [err, setErr] = useState(false)
 const load = () => { setErr(false); listInspections().then(setRows).catch(() => setErr(true)) }
 useEffect(load, [])
 if (err) return <ErrorState message="Couldn't load inspections" onRetry={load}/>
 if (!rows) return <LoadingState/>
 const total = rows.length
 const pass = rows.filter(r => r.status === 'pass').length
 const avg = total ? Math.round(rows.reduce((s, r) => s + r.score, 0) / total) : 0
 const passRate = total ? Math.round(pass / total * 100) : 0
 const anomalyRate = total ? Math.round((total - pass) / total * 100) : 0
 return <div className="space-y-6"><div><h1 className="text-xl font-semibold">Dashboard</h1><p className="text-sm text-slate-500">Live inspection overview connected to CLOCKIT API.</p></div>
  <div className="grid grid-cols-2 gap-4 xl:grid-cols-4"><StatCard label="Inspections" value={String(total)}/><StatCard label="Pass rate" value={`${passRate}%`} hint={`${total-pass} failed or under review`}/><StatCard label="Anomaly detection rate" value={`${anomalyRate}%`}/><StatCard label="Average quality score" value={String(avg)}/></div>
  <div className="grid gap-4 lg:grid-cols-3"><section className="rounded-lg border border-slate-200 bg-white p-4 lg:col-span-2"><h2 className="mb-2 font-medium">Inspection activity, last 7 days</h2>
   <div className="h-60"><ResponsiveContainer><LineChart data={trend}><XAxis dataKey="day"/><YAxis/><Tooltip/><Line dataKey="inspections" stroke="#2563eb" strokeWidth={2}/><Line dataKey="anomalies" stroke="#dc2626" strokeWidth={2}/></LineChart></ResponsiveContainer></div></section>
   <section className="rounded-lg border border-slate-200 bg-white p-4"><h2 className="mb-2 font-medium">Anomaly distribution</h2><div className="h-48"><ResponsiveContainer><PieChart><Pie data={distribution} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70}>{distribution.map((_, i) => <Cell key={i} fill={colors[i]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer></div>
    <ul className="mt-1 space-y-1 text-xs">{distribution.map((d, i) => <li key={d.name} className="flex items-center gap-2"><span className="h-2 w-2 rounded-full" style={{background:colors[i]}}/>{d.name} <span className="ml-auto text-slate-500">{d.value}</span></li>)}</ul></section></div>
  <div className="grid gap-4 lg:grid-cols-3"><section className="rounded-lg border border-slate-200 bg-white p-4 lg:col-span-2"><div className="mb-2 flex justify-between"><h2 className="font-medium">Recent inspections</h2><Link to="/history" className="text-sm text-blue-600">View all</Link></div>
   <table className="w-full text-sm"><tbody>{rows.slice(0,5).map(r => <tr key={r.id} className="border-t border-slate-100"><td className="py-2 font-medium">{r.id}</td><td>{r.product}</td><td className="text-slate-500">{r.industry}</td><td>{r.score}</td><td><StatusBadge value={r.status}/></td></tr>)}</tbody></table></section>
   <section className="rounded-lg border border-slate-200 bg-white p-4"><h2 className="mb-2 font-medium">Model performance</h2>{models.map(m => <div key={m.id} className="mb-3"><div className="flex justify-between text-sm"><span>{m.name}</span><span>{m.accuracy}%</span></div><div className="mt-1 h-1.5 rounded bg-slate-100"><div className="h-1.5 rounded bg-blue-600" style={{width:`${m.accuracy}%`}}/></div></div>)}</section></div></div> }
