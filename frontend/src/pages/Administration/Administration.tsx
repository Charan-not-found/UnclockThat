/**
 * Administration page — seed database, view system status.
 */
import { useState } from 'react'
import { Database, AlertCircle, CheckCircle2 } from 'lucide-react'
import Button from '../../components/common/Button'

export default function Administration() {
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState<{ message: string; created_models: string[]; created_manufacturer: boolean; created_pipeline: boolean } | null>(null)
  const [seedErr, setSeedErr] = useState('')

  const runSeed = async () => {
    setSeeding(true)
    setSeedResult(null)
    setSeedErr('')
    try {
      const { seedDatabase } = await import('../../services/adminService')
      const result = await seedDatabase()
      setSeedResult(result)
    } catch (e: any) {
      setSeedErr(e?.response?.data?.detail ?? 'Seed failed. Check backend logs.')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="page-header">
        <h1>Administration</h1>
        <p>System operations, database management, and configuration.</p>
      </div>

      {/* Database seed */}
      <section className="card p-5">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-blue-100">
            <Database size={20} className="text-blue-600" />
          </div>
          <div className="flex-1">
            <h2 className="font-medium">Seed database</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Registers the downloaded pretrained model weights (EfficientAD-Small, EfficientAD-Medium, YOLO11n-Seg)
              and creates a default manufacturer + pipeline. Idempotent — safe to run multiple times.
            </p>
            <div className="mt-3 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-800">
              <strong>Note:</strong> Downloaded weights are registered as <em>Disabled</em> — they require student network
              training (EfficientAD) or fine-tuning (YOLO) before they can run real inference. The OpenCV heuristic
              is registered as the only currently <em>Ready</em> model.
            </div>

            <Button className="mt-3" size="sm" loading={seeding} onClick={runSeed}>
              Run seed
            </Button>

            {seedErr && (
              <div className="mt-3 flex items-start gap-2 rounded-md bg-red-50 border border-red-200 px-3 py-2 text-xs text-red-700">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                {seedErr}
              </div>
            )}

            {seedResult && (
              <div className="mt-3 rounded-md bg-green-50 border border-green-200 px-3 py-3 text-xs text-green-800 space-y-1">
                <div className="flex items-center gap-1.5 font-medium">
                  <CheckCircle2 size={14} /> Seed completed
                </div>
                <p>{seedResult.message}</p>
                <ul className="mt-1 list-disc list-inside space-y-0.5">
                  <li>Manufacturer created: {seedResult.created_manufacturer ? 'Yes' : 'Already existed'}</li>
                  <li>Pipeline created: {seedResult.created_pipeline ? 'Yes' : 'Already existed'}</li>
                  <li>Models created: {seedResult.created_models.length === 0 ? 'Already registered' : seedResult.created_models.join(', ')}</li>
                </ul>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Planned features */}
      <section className="card p-5">
        <h2 className="font-medium mb-3">Planned administration features</h2>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {[
            ['Organization management', 'Milestone 7'],
            ['Facilities & production lines', 'Milestone 7'],
            ['User & role management', 'Milestone 7'],
            ['Audit log viewer', 'Milestone 7'],
            ['Dataset management', 'Milestone 3'],
            ['Training job management', 'Milestone 5'],
          ].map(([feat, milestone]) => (
            <div key={feat} className="flex justify-between rounded-md bg-slate-50 px-3 py-2">
              <span className="text-slate-600">{feat}</span>
              <span className="text-xs text-slate-400 font-medium">{milestone}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-400">
          These features are labelled Unavailable until their backend APIs and authentication are implemented.
          They will not appear as navigable pages until they are complete.
        </p>
      </section>
    </div>
  )
}
