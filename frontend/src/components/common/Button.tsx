import type { FC, ButtonHTMLAttributes, ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

const VARIANTS = {
  primary:   'bg-blue-600 text-white hover:bg-blue-700 border-transparent disabled:bg-blue-300',
  secondary: 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50 disabled:opacity-50',
  danger:    'bg-red-600 text-white hover:bg-red-700 border-transparent disabled:opacity-50',
  ghost:     'bg-transparent text-slate-600 border-transparent hover:bg-slate-100 disabled:opacity-50',
}
const SIZES = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-3.5 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
}

const Button: FC<Props> = ({ variant = 'primary', size = 'md', loading, children, className = '', disabled, ...rest }) => (
  <button
    {...rest}
    disabled={disabled || loading}
    className={`inline-flex items-center gap-2 rounded-md border font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
  >
    {loading && <Loader2 size={14} className="animate-spin" aria-hidden />}
    {children}
  </button>
)

export default Button
