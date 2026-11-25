import { useState } from 'react'
import { Upload, Play, CheckCircle2 } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { ErrorState } from '../../components/common/LoadingState'
import { industries, pipelines } from '../../services/mockData'
import { confirmInspection, runInspection } from '../../services/inspectionService'
import type { InspectionResult } from '../../types'
const field = 'mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm'
export default function Inspection() {
 const [industry, setIndustry] = useState('Automotive'); const [product, setProduct] = useState(industries.Automotive[0]); const [pipelineId, setPipelineId] = useState(pipelines[0].id)
 const [threshold, setThreshold] = useState(0.5); const [file, setFile] = useState<File>(); const [url, setUrl] = useState<string>()
 const [busy, setBusy] = useState(false); const [progress, setProgress] = useState(0); const [result, setResult] = useState<InspectionResult>(); const [err, setErr] = useState(false)
 const [confirm, setConfirm] = useState(false); const [confirmed, setConfirmed] = useState(false)
 const pick = (f?: File) => { if (!f) return; setFile(f); setUrl(URL.createObjectURL(f)); setResult(undefined); setConfirmed(false) }
 const run = async () => {
  if (!file) return; setBusy(true); setErr(false); setResult(undefined); setProgress(0)
  const t = setInterval(() => setProgress(p => Math.min(p + 8, 95)), 200)
  try { setResult(await runInspection({ industry, product, pipelineId, threshold, fileName: file.name }, file)); setProgress(100) } catch { setErr(true) } finally { clearInterval(t); setBusy(false) } }
 return <div className="space-y-4"><h1 className="text-xl font-semibold">New Inspection</h1>
  <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
   <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
    <label className="block text-sm font-medium">Industry<select className={field} value={industry} onChange={e => { setIndustry(e.target.value); setProduct(industries[e.target.value][0]) }}>{Object.keys(industries).map(i => <option key={i}>{i}</option>)}</select></label>
    <label className="block text-sm font-medium">Product<select className={field} value={product} onChange={e => setProduct(e.target.value)}>{industries[industry].map(p => <option key={p}>{p}</option>)}</select></label>
    <label className="block text-sm font-medium">Pipeline<select className={field} value={pipelineId} onChange={e => setPipelineId(e.target.value)}>{pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
    <label className="block text-sm font-medium">Anomaly threshold: {threshold.toFixed(2)}<input type="range" min={0} max={1} step={0.05} value={threshold} onChange={e => setThreshold(+e.target.value)} className="mt-1 w-full"/></label>
    <label className="flex cursor-pointer flex-col items-center rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500 hover:bg-slate-50"><Upload size={20}/><span className="mt-1">{file ? file.name : 'Choose an image'}</span><input type="file" accept="image/*" className="sr-only" onChange={e => pick(e.target.files?.[0])}/></label>
    <Button className="w-full justify-center" disabled={!file || busy} onClick={run}><Play size={15}/>{busy ? 'Running…' : 'Run inspection'}</Button></section>
   <section className="rounded-lg border border-slate-200 bg-white p-4">
    {!url && <div className="p-16 text-center text-slate-500"><p className="font-medium text-slate-700">No image yet</p><p className="text-sm">Upload an image and run an inspection to see results here.</p></div>}
    {busy && <div className="mb-3"><div className="h-2 rounded bg-slate-100"><div className="h-2 rounded bg-blue-600 transition-all" style={{width:`${progress}%`}}/></div><p className="mt-1 text-xs text-slate-500">Processing {progress}%</p></div>}
    {err && <ErrorState message="Inspection failed" onRetry={run}/>}
    {url && <div className="grid gap-3 md:grid-cols-2">
     <figure><img src={url} alt="Original" className="aspect-square w-full rounded-md bg-slate-100 object-contain"/><figcaption className="mt-1 text-xs text-slate-500">Original</figcaption></figure>
     <figure><div className="relative aspect-square overflow-hidden rounded-md bg-slate-100"><img src={url} alt="Heatmap" className="h-full w-full object-contain"/>
      {result && result.defects.map((d, i) => <div key={i}><div className="absolute rounded-full" style={{left:`${d.box.x-6}%`,top:`${d.box.y-6}%`,width:`${d.box.w+12}%`,height:`${d.box.h+12}%`,background:'radial-gradient(circle,rgba(220,38,38,.55),transparent 70%)'}}/><div className="absolute border-2 border-red-600" style={{left:`${d.box.x}%`,top:`${d.box.y}%`,width:`${d.box.w}%`,height:`${d.box.h}%`}}/></div>)}</div>
      <figcaption className="mt-1 text-xs text-slate-500">Anomaly heatmap and localization</figcaption></figure></div>}
    {result && <div className="mt-4 space-y-3">{result.isMock && <div className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">Mock result — canned output, not real AI inference. Backend not connected.</div>}
     <div className="flex items-center gap-3"><span className="text-3xl font-semibold">{result.score}</span><span className="text-sm text-slate-500">aggregated quality score</span><StatusBadge value={result.status}/></div>
     <table className="w-full text-sm"><thead className="text-left text-slate-500"><tr><th className="py-1">Defect</th><th>Severity</th><th>Confidence</th><th>Anomaly score</th></tr></thead><tbody>{result.defects.map((d, i) => <tr key={i} className="border-t border-slate-100"><td className="py-2">{d.type}</td><td><StatusBadge value={d.severity}/></td><td>{Math.round(d.confidence*100)}%</td><td>{d.anomalyScore.toFixed(2)}</td></tr>)}</tbody></table>
     {confirmed ? <p className="flex items-center gap-2 text-sm text-green-700"><CheckCircle2 size={16}/>Result confirmed</p> : <Button onClick={() => setConfirm(true)}>Review and confirm</Button>}</div>}</section></div>
  <Modal open={confirm} title="Confirm inspection result?" confirmLabel="Confirm result" onCancel={() => setConfirm(false)} onConfirm={async () => { if (result?.inspectionId) await confirmInspection(result.inspectionId); setConfirmed(true); setConfirm(false) }}>This records the result as reviewed for {product}.</Modal></div> }
