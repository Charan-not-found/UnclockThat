import type { FC, ReactNode } from 'react'

interface Props {
  label: string
  value: string | number
  hint?: string
  accent?: 'default' | 'green' | 'red' | 'amber'
  icon?: ReactNode
}

const ACCENTS = {
  default: 'text-blue-600',
  green:   'text-green-600',
  red:     'text-red-600',
  amber:   'text-amber-600',
}

const StatCard: FC<Props> = ({ label, value, hint, accent = 'default', icon }) => (
  <div className="card p-4">
    <div className="flex items-start justify-between">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      {icon && <span className="text-slate-400">{icon}</span>}
    </div>
    <p className={`mt-1 text-2xl font-semibold tabular-nums ${ACCENTS[accent]}`}>{value}</p>
    {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
  </div>
)

export default StatCard
