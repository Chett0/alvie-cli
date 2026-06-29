import { useState } from 'react'

function HypothesisCard({ index, runCount, defaultOpen = false, children }) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="accordion hypothesis-accordion mb-2">
      <div
        className={`accordion-item shadow-sm hypothesis-item ${
          isOpen ? 'hypothesis-item-open' : ''
        }`}
      >
        <h2 className="accordion-header">
          <button
            type="button"
            className={`accordion-button fw-semibold fs-5 ${
              isOpen ? '' : 'collapsed'
            }`}
            onClick={() => setIsOpen((current) => !current)}
            aria-expanded={isOpen}
          >
            <span className="d-flex justify-content-between align-items-center w-100 me-3">
              <span>Hypothesis {index+1}</span>
              <span className="text-secondary fw-normal fs-6">
                {runCount} {runCount === 1 ? 'run' : 'runs'}
              </span>
            </span>
          </button>
        </h2>

        <div className={`accordion-collapse collapse ${isOpen ? 'show' : ''}`}>
          {isOpen && <div className="accordion-body">{children}</div>}
        </div>
      </div>
    </div>
  )
}

export default HypothesisCard
