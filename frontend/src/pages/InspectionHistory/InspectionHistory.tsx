import { useEffect, useMemo, useState } from 'react'
import { Download, Search } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import { LoadingState, EmptyState, ErrorState } from '../../components/common/LoadingState'
import { listInspections } from '../../services/inspectionService'
import type { Inspection } from '../../types'
const sel = 'rounded-md border border-slate-300 bg-white px-2 py-2 text-sm'
export default function InspectionHistory() {
 const [rows, setRows] = useState<Inspection[]>(); const [err, setErr] = useState(false)
 const [q, setQ] = useState(''); const [status, setStatus] = useState(''); const [industry, setIndustry] = useState(''); const [severity, setSeverity] = useState(''); const [open, setOpen] = useState<Inspection>()
 const load = () => { setErr(false); listInspections().then(setRows).catch(() => setErr(true)) }
 useEffect(load, [])
 const shown = useMemo(() => (rows ?? []).filter(r => (!q || `${r.id} ${r.product}`.toLowerCase().includes(q.toLowerCase())) && (!status || r.status === status) && (!industry || r.industry === industry) && (!severity || r.severity === severity)), [rows, q, status, industry, severity])
 const exportCsv = () => { const csv = ['id,date,industry,product,status,score', ...shown.map(r => [r.id, r.date, r.industry, r.product, r.status, r.score].join(','))].join('\n'); const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type:'text/csv' })); a.download = 'inspections.csv'; a.click() }
 if (err) return <ErrorState message="Couldn't load history" onRetry={load}/>
 if (!rows) return <LoadingState/>
 return <div className="space-y-4"><div className="flex items-center justify-between"><h1 className="text-xl font-semibold">Inspection History</h1><Button variant="secondary" onClick={exportCsv}><Download size={15}/>Export CSV</Button></div>
  <div className="flex flex-wrap gap-2"><div className="relative"><Search size={15} className="absolute left-2.5 top-3 text-slate-400"/><input value={q} onChange={e => setQ(e.target.value)} placeholder="Search ID or product" className={`${sel} pl-8`}/></div>
   <select className={sel} value={status} onChange={e => setStatus(e.target.value)}><option value="">All statuses</option><option value="pass">Pass</option><option value="fail">Fail</option><option value="review">Review</option></select>
   <select className={sel} value={industry} onChange={e => setIndustry(e.target.value)}><option value="">All industries</option><option>Automotive</option><option>Electronics</option><option>Textile</option></select>
   <select className={sel} value={severity} onChange={e => setSeverity(e.target.value)}><option value="">All severities</option><option value="none">None</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></div>
  <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">{shown.length === 0 ? <EmptyState title="No inspections match" hint="Clear a filter to see more."/> :
   <table className="w-full text-sm"><thead className="bg-slate-50 text-left text-slate-500"><tr>{['ID','Date','Industry','Product','Score','Severity','Status'].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
    <tbody>{shown.map(r => <tr key={r.id} onClick={() => setOpen(r)} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50"><td className="px-3 py-2 font-medium">{r.id}</td><td className="px-3">{new Date(r.date).toLocaleString()}</td><td className="px-3">{r.industry}</td><td className="px-3">{r.product}</td><td className="px-3">{r.score}</td><td className="px-3"><StatusBadge value={r.severity}/></td><td className="px-3"><StatusBadge value={r.status}/></td></tr>)}</tbody></table>}</div>
  {open && <aside className="fixed inset-y-0 right-0 z-40 w-80 border-l border-slate-200 bg-white p-5 shadow-xl"><div className="flex justify-between"><h2 className="font-semibold">{open.id}</h2><button onClick={() => setOpen(undefined)} className="text-slate-500">Close</button></div>
   <dl className="mt-4 space-y-2 text-sm">{([['Product', open.product], ['Industry', open.industry], ['Pipeline', open.pipeline], ['Score', open.score], ['Defects found', open.defects]] as const).map(([k, v]) => <div key={k} className="flex justify-between"><dt className="text-slate-500">{k}</dt><dd className="text-right">{v}</dd></div>)}</dl></aside>}</div> }
