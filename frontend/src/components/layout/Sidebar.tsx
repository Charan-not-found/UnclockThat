import { NavLink } from 'react-router-dom'
import { LayoutDashboard, ScanSearch, History, Workflow, Cpu, Database, Dumbbell, BarChart3, Settings } from 'lucide-react'
export const nav = [
 { to:'/', label:'Dashboard', icon:LayoutDashboard }, { to:'/inspect', label:'New Inspection', icon:ScanSearch }, { to:'/history', label:'Inspection History', icon:History },
 { to:'/pipelines', label:'Pipeline Builder', icon:Workflow }, { to:'/models', label:'Models', icon:Cpu }, { to:'/datasets', label:'Datasets', icon:Database },
 { to:'/training', label:'Training Center', icon:Dumbbell }, { to:'/analytics', label:'Analytics & Reports', icon:BarChart3 }, { to:'/settings', label:'Settings', icon:Settings } ]
export default function Sidebar() {
 return <aside className="flex w-60 shrink-0 flex-col bg-ink-900 text-slate-300"><div className="px-5 py-5 text-lg font-semibold tracking-wide text-white">CLOCKIT</div>
  <nav className="flex-1 space-y-0.5 px-2">{nav.map(({ to, label, icon: I }) => <NavLink key={to} to={to} end={to==='/'} className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 text-sm ${isActive ? 'bg-blue-600 text-white' : 'hover:bg-ink-700'}`}><I size={17}/>{label}</NavLink>)}</nav></aside> }
