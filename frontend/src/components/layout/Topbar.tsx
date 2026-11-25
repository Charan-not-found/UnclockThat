import { useLocation, Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { nav } from './Sidebar'
export default function Topbar() {
 const { pathname } = useLocation(); const cur = nav.find(n => n.to === pathname)?.label ?? 'Dashboard'
 return <header className="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
  <div className="text-sm text-slate-500"><Link to="/" className="hover:text-slate-800">Home</Link> / <span className="font-medium text-slate-800">{cur}</span></div>
  <div className="flex items-center gap-4"><button aria-label="Notifications" className="text-slate-500 hover:text-slate-800"><Bell size={18}/></button><div className="grid h-8 w-8 place-items-center rounded-full bg-blue-600 text-xs font-medium text-white">AD</div></div></header> }
