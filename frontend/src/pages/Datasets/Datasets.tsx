/**
 * Datasets page — planned for Milestone 3.
 * Shown as Unavailable until backend dataset upload/versioning API exists.
 */
import { Database } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Datasets() {
  return (
    <div className="space-y-4">
      <div className="page-header">
        <h1>Datasets</h1>
        <p>Dataset upload, versioning, and lineage management.</p>
      </div>
      <div className="card p-10 flex flex-col items-center text-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
          <Database size={28} className="text-slate-400" />
        </div>
        <h2 className="font-semibold text-slate-700">Datasets — Unavailable</h2>
        <p className="max-w-md text-sm text-slate-500">
          Dataset management (upload wizard, duplicate/leakage detection, immutable versioning,
          train/validation/test split management) requires backend <code>/datasets</code> and
          <code>/dataset-versions</code> APIs that are not yet implemented.
        </p>
        <p className="text-xs text-slate-400 mt-1">Planned: Milestone 3</p>
        <Link to="/admin" className="text-sm text-blue-600 hover:underline">Go to Administration →</Link>
      </div>
    </div>
  )
}
