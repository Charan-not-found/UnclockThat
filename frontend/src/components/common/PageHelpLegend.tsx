/**
 * PageHelpLegend — "?" button that opens a dark-theme-aware legend modal
 * explaining statuses, severity levels, and workflow for each page.
 */
import { useState, type FC } from 'react'
import { HelpCircle } from 'lucide-react'
import Modal from './Modal'
import StatusBadge from './StatusBadge'

export interface LegendItem {
  label: string
  badge?: string
  description: string
}

interface Props {
  title: string
  summary: string
  items: LegendItem[]
}

const PageHelpLegend: FC<Props> = ({ title, summary, items }) => {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`${title} legend and help`}
        title="Page legend & help"
        className="inline-flex h-7 w-7 items-center justify-center rounded-full border text-xs font-semibold transition-colors input-field hover:border-blue-500 hover:text-blue-500"
      >
        <HelpCircle size={15} />
      </button>

      <Modal open={open} title={`${title} — Legend`} onCancel={() => setOpen(false)}>
        <div className="space-y-3">
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>{summary}</p>
          <div className="space-y-2">
            {items.map((item, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-md border p-2.5 popup-subtle">
                <div className="shrink-0 pt-0.5">
                  {item.badge ? (
                    <StatusBadge value={item.badge} />
                  ) : (
                    <span className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                      {item.label}
                    </span>
                  )}
                </div>
                <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
                  {item.badge && (
                    <span className="font-medium mr-1" style={{ color: 'var(--color-text-primary)' }}>
                      {item.label}:
                    </span>
                  )}
                  {item.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Modal>
    </>
  )
}

export default PageHelpLegend
