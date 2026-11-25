/**
 * Pipelines page — list all configured pipelines, create new, toggle active.
 */
import { useEffect, useState } from 'react'
import { Plus, RefreshCw } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import Modal from '../../components/common/Modal'
import { LoadingState, ErrorState, EmptyState } from '../../components/common/LoadingState'
import { listPipelines, createPipeline, togglePipeline } from '../../services/pipelineService'
import type { Pipeline } from '../../types'

export default function Pipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>()
  const [err, setErr] = useState(false)
  const [toggling, setToggling] = useState<string>()
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newMfg, setNewMfg] = useState('Default Manufacturer')

  const load = () => {
    setErr(false)
    setPipelines(undefined)
    listPipelines().then(setPipelines).catch(() => setErr(true))
  }

  useEffect(load, [])

  const handleToggle = async (p: Pipeline) => {
    setToggling(p.id)
    try {
      const updated = await togglePipeline(p.id)
      setPipelines(prev => prev?.map(x => x.id === p.id ? updated : x))
    } finally {
      setToggling(undefined)
    }
  }

  const handleCreate = async () => {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createPipeline({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        manufacturer_name: newMfg.trim() || 'Default Manufacturer',
        stages: [],
      })
      setCreateOpen(false)
      setNewName('')
      setNewDesc('')
      load()
    } finally {
      setCreating(false)
    }
  }

  if (!pipelines && !err) return <LoadingState message="Loading pipelines…" />
  if (err) return <ErrorState message="Failed to load pipelines" onRetry={load} />

  const FIELD = 'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 page-header">
        <div>
          <h1>Pipelines</h1>
          <p>{pipelines?.length ?? 0} pipeline configuration{pipelines?.length !== 1 ? 's' : ''} in the database.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}><Plus size={14} />New pipeline</Button>
        </div>
      </div>

      {pipelines?.length === 0 ? (
        <div className="card">
          <EmptyState
            title="No pipelines configured"
            body="Create your first pipeline or run the admin seed to create a default."
            action={<Button size="sm" onClick={() => setCreateOpen(true)}><Plus size={14} />New pipeline</Button>}
          />
        </div>
      ) : (
        <section className="card">
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr><th>Name</th><th>Version</th><th>Manufacturer</th><th>Stages</th><th>State</th><th>Created</th><th>Action</th></tr>
              </thead>
              <tbody>
                {pipelines?.map(p => (
                  <tr key={p.id}>
                    <td>
                      <p className="font-medium">{p.name}</p>
                      {p.description && <p className="text-xs text-slate-400">{p.description}</p>}
                    </td>
                    <td className="font-mono text-xs">{p.version}</td>
                    <td className="text-slate-500 text-sm">{p.manufacturer}</td>
                    <td className="tabular-nums">{p.stages.length}</td>
                    <td><StatusBadge value={p.state} /></td>
                    <td className="text-xs text-slate-400">{new Date(p.created_at).toLocaleDateString()}</td>
                    <td>
                      <Button variant="ghost" size="sm" loading={toggling === p.id} onClick={() => handleToggle(p)}>
                        {p.is_active ? 'Disable' : 'Enable'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Stage detail cards */}
      {pipelines && pipelines.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-slate-700 mb-2">Pipeline stage details</h2>
          <div className="grid gap-3 lg:grid-cols-2">
            {pipelines.map(p => p.stages.length > 0 && (
              <div key={p.id} className="card p-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-medium text-sm">{p.name}</p>
                  <StatusBadge value={p.state} size="sm" />
                </div>
                <div className="space-y-1">
                  {p.stages.map((s, i) => (
                    <div key={i} className="rounded-md bg-slate-50 px-3 py-2 text-xs">
                      <div className="flex justify-between">
                        <span className="font-medium">{s.label || s.id}</span>
                        <span className="text-slate-400 font-mono">{s.type}</span>
                      </div>
                      {s.note && <p className="text-slate-400 mt-0.5">{s.note}</p>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Create modal */}
      <Modal
        open={createOpen}
        title="New Pipeline"
        confirmLabel="Create pipeline"
        onCancel={() => setCreateOpen(false)}
        onConfirm={handleCreate}
        confirmDisabled={!newName.trim()}
        confirmLoading={creating}
      >
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-700">Pipeline name <span className="text-red-500">*</span></label>
            <input className={FIELD} value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Surface defect detection" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Description</label>
            <input className={FIELD} value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Optional description" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Manufacturer name</label>
            <input className={FIELD} value={newMfg} onChange={e => setNewMfg(e.target.value)} />
          </div>
          <p className="text-xs text-slate-400">
            Stages can be added via the API after creation. Stage editor UI is planned for Milestone 4.
          </p>
        </div>
      </Modal>
    </div>
  )
}
