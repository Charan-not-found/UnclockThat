import type { ButtonHTMLAttributes } from 'react'
const v = { primary:'bg-blue-600 text-white hover:bg-blue-700', secondary:'bg-white border border-slate-300 hover:bg-slate-50', danger:'bg-red-600 text-white hover:bg-red-700' }
export default function Button({ variant='primary', className='', ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof v }) {
 return <button {...p} className={`inline-flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium disabled:opacity-50 ${v[variant]} ${className}`} /> }
