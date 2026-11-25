/**
 * Settings page — environment-level configuration.
 */
import { Settings as SettingsIcon } from 'lucide-react'

export default function Settings() {
  return (
    <div className="space-y-4">
      <div className="page-header">
        <h1>Settings</h1>
        <p>Application and environment configuration.</p>
      </div>

      <section className="card p-5">
        <h2 className="font-medium mb-3">Environment</h2>
        <div className="grid gap-2 text-sm">
          {[
            ['API base URL', (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1'],
            ['Environment', import.meta.env.MODE],
            ['Frontend version', '0.1-prototype'],
          ].map(([k, v]) => (
            <div key={k} className="flex flex-wrap gap-2 rounded-md bg-slate-50 px-3 py-2">
              <span className="text-slate-500 w-32 flex-shrink-0">{k}</span>
              <span className="font-mono text-slate-800 break-all">{v}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="card p-5">
        <h2 className="font-medium mb-2">Planned settings</h2>
        <ul className="text-sm text-slate-500 space-y-1 list-disc list-inside">
          <li>Theme (light / dark / system)</li>
          <li>Default inspection threshold</li>
          <li>Notification preferences</li>
          <li>API key / auth token management</li>
          <li>Hardware / device configuration</li>
        </ul>
        <p className="text-xs text-slate-400 mt-2">These settings require backend auth and user preferences API — Milestone 7.</p>
      </section>
    </div>
  )
}
