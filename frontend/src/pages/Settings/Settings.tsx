/**
 * Settings page — global AI model enable/disable switches + environment info.
 */
import { useEffect, useState } from 'react'
import { Cpu, RefreshCw } from 'lucide-react'
import Button from '../../components/common/Button'
import StatusBadge from '../../components/common/StatusBadge'
import PageHelpLegend from '../../components/common/PageHelpLegend'
import { LoadingState, ErrorState } from '../../components/common/LoadingState'
import { listModelToggles, toggleModelSetting, type ModelToggleSetting } from '../../services/settingsService'
import { classifyError } from '../../services/api'

export default function Settings() {
  const [models, setModels] = useState<ModelToggleSetting[]>()
  const [err, setErr] = useState<string>()
  const [toggling, setToggling] = useState<string>()

  const load = async () => {
    setErr(undefined)
    try {
      setModels(await listModelToggles())
    } catch (e) {
      setErr(classifyError(e).message)
    }
  }

  useEffect(() => { void load() }, [])

  const handleToggle = async (modelKey: string) => {
    setToggling(modelKey)
    try {
      const updated = await toggleModelSetting(modelKey)
      setModels(prev => prev?.map(m => m.model_key === modelKey ? updated : m))
    } finally {
      setToggling(undefined)
    }
  }

  if (!models && !err) return <LoadingState message="Loading settings…" />
  if (err) return <ErrorState message="Failed to load settings" detail={err} onRetry={load} />

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3 page-header">
        <div>
          <div className="flex items-center gap-2">
            <h1>Settings</h1>
            <PageHelpLegend
              title="Settings"
              summary="Enable or disable AI models application-wide. Disabled models cannot be selected for new Scanner Unit modules or training runs."
              items={[
                { label: 'Enabled', badge: 'Ready', description: 'Model is available in Scanner Units and Training.' },
                { label: 'Disabled', badge: 'Disabled', description: 'Model is turned off across the application.' },
              ]}
            />
          </div>
          <p>Application-wide AI model toggles and runtime environment configuration.</p>
        </div>
        <Button variant="ghost" size="sm" onClick={load}><RefreshCw size={14} />Refresh</Button>
      </div>

      {/* Global AI Model Toggle Switches */}
      <section className="card p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Cpu size={18} className="text-blue-500" />
          <div>
            <h2 className="font-medium">AI Model Availability</h2>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              Toggle which AI models are enabled in Scanner Units and Training Center.
            </p>
          </div>
        </div>

        <div className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
          {models?.map(m => {
            const busy = toggling === m.model_key
            return (
              <div key={m.model_key} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-sm" style={{ color: 'var(--color-text-primary)' }}>
                      {m.display_name}
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--color-text-muted)' }}>
                      {m.model_family}
                    </span>
                    <StatusBadge value={m.is_enabled ? 'Ready' : 'Disabled'} />
                  </div>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>{m.task}</p>
                </div>

                {/* Accessible Toggle Switch */}
                <button
                  type="button"
                  role="switch"
                  aria-checked={m.is_enabled}
                  aria-label={`Toggle ${m.display_name}`}
                  disabled={busy}
                  onClick={() => handleToggle(m.model_key)}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
                    m.is_enabled ? 'bg-blue-600' : 'bg-slate-400 dark:bg-slate-600'
                  } ${busy ? 'opacity-50' : ''}`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow transition ${
                      m.is_enabled ? 'translate-x-5' : 'translate-x-0'
                    }`}
                  />
                </button>
              </div>
            )
          })}
        </div>
      </section>

      {/* Environment */}
      <section className="card p-5">
        <h2 className="font-medium mb-3">Environment</h2>
        <div className="grid gap-2 text-sm">
          {[
            ['API base URL', (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1'],
            ['Environment', import.meta.env.MODE],
            ['Frontend version', '1.1.0'],
          ].map(([k, v]) => (
            <div key={k} className="flex flex-wrap gap-2 rounded-md px-3 py-2 popup-subtle border">
              <span className="w-32 flex-shrink-0" style={{ color: 'var(--color-text-secondary)' }}>{k}</span>
              <span className="font-mono break-all" style={{ color: 'var(--color-text-primary)' }}>{v}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
