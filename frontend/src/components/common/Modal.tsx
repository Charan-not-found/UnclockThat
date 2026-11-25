import type { ReactNode } from 'react'
import Button from './Button'
export default function Modal({ open, title, children, onCancel, onConfirm, confirmLabel='Confirm' }: { open: boolean; title: string; children: ReactNode; onCancel: () => void; onConfirm: () => void; confirmLabel?: string }) {
 if (!open) return null
 return <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 grid place-items-center bg-slate-900/50 p-4"><div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
  <h2 className="text-lg font-semibold">{title}</h2><div className="mt-2 text-sm text-slate-600">{children}</div>
  <div className="mt-5 flex justify-end gap-2"><Button variant="secondary" onClick={onCancel}>Cancel</Button><Button onClick={onConfirm}>{confirmLabel}</Button></div></div></div> }
