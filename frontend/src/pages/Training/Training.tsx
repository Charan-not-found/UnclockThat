/**
 * Training page — planned for Milestone 5.
 * Shown as Unavailable until real training job APIs exist.
 */
import { Dumbbell } from 'lucide-react'

export default function Training() {
  return (
    <div className="space-y-4">
      <div className="page-header">
        <h1>Training</h1>
        <p>Model training jobs, monitoring, and evaluation.</p>
      </div>
      <div className="card p-10 flex flex-col items-center text-center gap-3">
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
          <Dumbbell size={28} className="text-slate-400" />
        </div>
        <h2 className="font-semibold text-slate-700">Training Center — Unavailable</h2>
        <p className="max-w-md text-sm text-slate-500">
          Training job creation, real-event progress monitoring, checkpoint management,
          and evaluation report generation require the <code>backend/app/models/</code> AI subsystem
          and <code>/training-jobs</code> APIs — not yet implemented.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Currently available pretrained weights: <strong>pretrained_teacher_small.pth</strong>,
          <strong> pretrained_teacher_medium.pth</strong>, <strong>yolo11n-seg.pt</strong>.
          These require training/fine-tuning before inference.
        </p>
        <p className="text-xs text-slate-400 mt-1">Planned: Milestone 5</p>
      </div>
    </div>
  )
}
