import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function MainLayout() {
  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6" id="main-content">
        <Outlet />
      </main>
    </div>
  )
}
