import type { FC, ReactNode } from 'react'
import { X } from 'lucide-react'
import Button from './Button'

interface Props {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  onConfirm?: () => void | Promise<void>
  onCancel: () => void
  dangerous?: boolean
  confirmDisabled?: boolean
  confirmLoading?: boolean
}

const Modal: FC<Props> = ({
  open, title, children, confirmLabel = 'Confirm', cancelLabel = 'Cancel',
  onConfirm, onCancel, dangerous, confirmDisabled, confirmLoading,
}) => {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal aria-labelledby="modal-title">
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <h2 id="modal-title" className="font-semibold text-slate-900">{title}</h2>
          <button onClick={onCancel} className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4 text-sm text-slate-700">{children}</div>
        {onConfirm && (
          <div className="flex justify-end gap-2 border-t border-slate-200 px-5 py-3">
            <Button variant="secondary" size="sm" onClick={onCancel}>{cancelLabel}</Button>
            <Button variant={dangerous ? 'danger' : 'primary'} size="sm" onClick={onConfirm} disabled={confirmDisabled} loading={confirmLoading}>
              {confirmLabel}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default Modal
