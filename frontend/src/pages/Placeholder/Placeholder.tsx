import { Construction } from 'lucide-react'
export default function Placeholder({ title }: { title: string }) {
 return <div><h1 className="text-xl font-semibold">{title}</h1><div className="mt-6 flex flex-col items-center rounded-lg border border-dashed border-slate-300 bg-white p-14 text-slate-500"><Construction/><p className="mt-2 font-medium text-slate-700">Not built yet</p><p className="text-sm">This page is next in the development order.</p></div></div> }
