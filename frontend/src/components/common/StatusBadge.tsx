/**
 * StatusBadge — renders spec-correct status and severity labels.
 * Color + icon + text: never color alone.
 */
import type { FC } from 'react'

interface Props { value: string; size?: 'sm' | 'md' }

const CONFIG: Record<string, { bg: string; text: string; dot: string }> = {
  // Spec status vocabulary
  'Completed':    { bg: 'bg-green-50',   text: 'text-green-800',  dot: 'bg-green-500'  },
  'Approved':     { bg: 'bg-green-50',   text: 'text-green-800',  dot: 'bg-green-600'  },
  'Failed':       { bg: 'bg-red-50',     text: 'text-red-800',    dot: 'bg-red-500'    },
  'Rejected':     { bg: 'bg-red-50',     text: 'text-red-800',    dot: 'bg-red-600'    },
  'Needs review':      { bg: 'bg-amber-50',   text: 'text-amber-800',  dot: 'bg-amber-500'  },
  'Needs dataset':     { bg: 'bg-amber-50',   text: 'text-amber-800',  dot: 'bg-amber-500'  },
  'Training':          { bg: 'bg-blue-50',    text: 'text-blue-800',   dot: 'bg-blue-500'   },
  'Validated':         { bg: 'bg-green-50',   text: 'text-green-800',  dot: 'bg-green-500'  },
  'Validation failed': { bg: 'bg-red-50',     text: 'text-red-800',    dot: 'bg-red-500'    },
  'Uploaded':          { bg: 'bg-sky-50',     text: 'text-sky-800',    dot: 'bg-sky-500'    },
  'Running':      { bg: 'bg-blue-50',    text: 'text-blue-800',   dot: 'bg-blue-500'   },
  'Queued':       { bg: 'bg-violet-50',  text: 'text-violet-800', dot: 'bg-violet-500' },
  'Ready':        { bg: 'bg-sky-50',     text: 'text-sky-800',    dot: 'bg-sky-500'    },
  'Configured':   { bg: 'bg-sky-50',     text: 'text-sky-800',    dot: 'bg-sky-400'    },
  'Draft':        { bg: 'bg-slate-100',  text: 'text-slate-700',  dot: 'bg-slate-400'  },
  'Disabled':     { bg: 'bg-slate-100',  text: 'text-slate-500',  dot: 'bg-slate-300'  },
  'Unavailable':  { bg: 'bg-slate-100',  text: 'text-slate-500',  dot: 'bg-slate-300'  },
  'Archived':     { bg: 'bg-slate-100',  text: 'text-slate-500',  dot: 'bg-slate-300'  },
  // Spec severity vocabulary
  'Critical':        { bg: 'bg-red-50',    text: 'text-red-800',   dot: 'bg-red-500'   },
  'Major':           { bg: 'bg-orange-50', text: 'text-orange-800',dot: 'bg-orange-500'},
  'Minor':           { bg: 'bg-yellow-50', text: 'text-yellow-800',dot: 'bg-yellow-500'},
  'Informational':   { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' },
  // Legacy compat
  'pass':    { bg: 'bg-green-50',  text: 'text-green-800', dot: 'bg-green-500'  },
  'fail':    { bg: 'bg-red-50',    text: 'text-red-800',   dot: 'bg-red-500'    },
  'review':  { bg: 'bg-amber-50',  text: 'text-amber-800', dot: 'bg-amber-500'  },
  'low':     { bg: 'bg-yellow-50', text: 'text-yellow-800',dot: 'bg-yellow-400' },
  'medium':  { bg: 'bg-orange-50', text: 'text-orange-800',dot: 'bg-orange-400' },
  'high':    { bg: 'bg-red-50',    text: 'text-red-800',   dot: 'bg-red-500'    },
  'none':    { bg: 'bg-slate-100', text: 'text-slate-500', dot: 'bg-slate-300'  },
}

const StatusBadge: FC<Props> = ({ value, size = 'sm' }) => {
  const cfg = CONFIG[value] ?? { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' }
  const pad = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${cfg.bg} ${cfg.text} ${pad}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} aria-hidden />
      {value}
    </span>
  )
}

export default StatusBadge
