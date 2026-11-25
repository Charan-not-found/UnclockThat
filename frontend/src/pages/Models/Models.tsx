import { useEffect, useState } from 'react'
import StatusBadge from '../../components/common/StatusBadge'
import { LoadingState } from '../../components/common/LoadingState'
import { listModels, toggleModel } from '../../services/modelService'
import type { ModelInfo } from '../../types'
export default function Models() {
 const [rows, setRows] = useState<ModelInfo[]>()
 useEffect(() => { listModels().then(setRows) }, [])
 if (!rows) return <LoadingState/>
 const toggle = async (id: string) => {
  const updated = await toggleModel(id)
  setRows(rows.map(m => m.id === id ? updated : m))
 }
 return <div className="space-y-4"><h1 className="text-xl font-semibold">Models</h1><div className="overflow-x-auto rounded-lg border border-slate-200 bg-white"><table className="w-full text-sm"><thead className="bg-slate-50 text-left text-slate-500"><tr>{['Name','Task','Version','Accuracy','Status',''].map(h => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}</tr></thead>
  <tbody>{rows.map(m => <tr key={m.id} className="border-t border-slate-100"><td className="px-3 py-2 font-medium">{m.name}</td><td className="px-3">{m.task}</td><td className="px-3">{m.version}</td><td className="px-3">{m.accuracy}%</td><td className="px-3"><StatusBadge value={m.enabled ? 'pass' : 'none'}/></td>
   <td className="px-3 text-right"><button onClick={() => toggle(m.id)} className="text-blue-600">{m.enabled ? 'Disable' : 'Enable'}</button></td></tr>)}</tbody></table></div></div> }
