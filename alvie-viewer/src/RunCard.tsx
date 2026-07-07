import { useState } from 'react'
import type { ReactNode } from 'react'

interface RunCardProps {
  index: number
  defaultOpen?: boolean
  children: ReactNode
}

function RunCard({ index, defaultOpen = false, children }: RunCardProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="accordion run-accordion mb-2">
      <div
        className={`accordion-item run-item ${isOpen ? 'run-item-open' : ''}`}
      >
        <h3 className="accordion-header">
          <button
            type="button"
            className={`accordion-button fw-semibold ${
              isOpen ? '' : 'collapsed'
            }`}
            onClick={() => setIsOpen((current) => !current)}
            aria-expanded={isOpen}
          >
            Run {index + 1}
          </button>
        </h3>

        <div className={`accordion-collapse collapse ${isOpen ? 'show' : ''}`}>
          {isOpen && <div className="accordion-body">{children}</div>}
        </div>
      </div>
    </div>
  )
}

export default RunCard
