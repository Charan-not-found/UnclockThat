import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, FlaskConical, ClipboardList, Cpu,
  Database, Dumbbell, BarChart3, Settings, Bell, Shield, Layers,
} from 'lucide-react'

const NAV = [
  { section: 'Inspect', items: [
    { to: '/',            label: 'Overview',           icon: LayoutDashboard },
    { to: '/scanners',    label: 'Scanner Units',      icon: Layers          },
    { to: '/test-sample', label: 'Test Sample',        icon: FlaskConical    },
    { to: '/history',     label: 'Inspection History', icon: ClipboardList   },
    { to: '/review',      label: 'Review Queue',       icon: Bell            },
  ]},
  { section: 'Data & AI', items: [
    { to: '/datasets',    label: 'Datasets',           icon: Database        },
    { to: '/training',    label: 'Training',           icon: Dumbbell        },
    { to: '/models',      label: 'AI Models',          icon: Cpu             },
  ]},
  { section: 'System', items: [
    { to: '/analytics',   label: 'Analytics',          icon: BarChart3       },
    { to: '/admin',       label: 'Administration',     icon: Shield          },
    { to: '/settings',    label: 'Settings',           icon: Settings        },
  ]},
]

const link = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
    isActive
      ? 'bg-blue-600 text-white font-medium'
      : 'text-slate-300 hover:bg-slate-700 hover:text-white'
  }`

export default function Sidebar() {
  return (
    <aside className="flex w-56 shrink-0 flex-col bg-slate-900 text-slate-300 border-r border-slate-800">
      <div className="px-4 py-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded bg-blue-600 flex items-center justify-center">
            <span className="text-white font-bold text-xs">CK</span>
          </div>
          <div>
            <div className="text-sm font-semibold text-white leading-none">CLOCKIT</div>
            <div className="text-xs text-slate-500 mt-0.5">Scanner Platform</div>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-4" aria-label="Main navigation">
        {NAV.map(({ section, items }) => (
          <div key={section}>
            <div className="px-3 mb-1 text-xs font-medium uppercase tracking-widest text-slate-500">
              {section}
            </div>
            <div className="space-y-0.5">
              {items.map(({ to, label, icon: Icon }) => (
                <NavLink key={to} to={to} end={to === '/'} className={link}>
                  <Icon size={16} aria-hidden />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-slate-800 text-xs text-slate-500">
        CLOCKIT / PROMETHEUS-X · v1.1
      </div>
    </aside>
  )
}
