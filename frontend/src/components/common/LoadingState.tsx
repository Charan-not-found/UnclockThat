import type { FC, ReactNode } from 'react'
import { AlertCircle, Loader2, ServerOff } from 'lucide-react'

export const LoadingState: FC<{ message?: string }> = ({ message = 'Loading…' }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
    <Loader2 size={28} className="animate-spin text-blue-500" aria-hidden />
    <p className="text-sm">{message}</p>
  </div>
)

export const ErrorState: FC<{ message: string; detail?: string; onRetry?: () => void }> = ({ message, detail, onRetry }) => (
  <div className="flex flex-col items-center justify-center gap-3 py-16" role="alert">
    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
      <ServerOff size={24} className="text-red-600" aria-hidden />
    </div>
    <p className="font-medium text-red-700">{message}</p>
    {detail && <p className="max-w-sm text-center text-xs text-red-500">{detail}</p>}
    {onRetry && (
      <button onClick={onRetry} className="mt-1 rounded-md bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">
        Retry
      </button>
    )}
  </div>
)

export const EmptyState: FC<{ title: string; body?: string; action?: ReactNode }> = ({ title, body, action }) => (
  <div className="flex flex-col items-center justify-center gap-2 py-16 text-slate-400">
    <AlertCircle size={28} aria-hidden />
    <p className="font-medium text-slate-600">{title}</p>
    {body && <p className="text-sm text-slate-400">{body}</p>}
    {action && <div className="mt-2">{action}</div>}
  </div>
)
