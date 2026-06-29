import { useEffect, useState } from 'react'
import HypothesisCard from './HypothesisCard'
import RunCard from './RunCard'
import StepsTable from './StepsTable'

// Pagination constants
const HYPOTHESES_PER_PAGE = 5
const RUNS_PER_PAGE = 10

function PaginatedHypothesis({ runs, hypothesisIndex }) {
  // Runs pagination
  const [page, setPage] = useState(1)
  const totalPages = Math.max(1, Math.ceil(runs.length / RUNS_PER_PAGE))
  
  // max of current available pages for filtering
  // E.g.: current_page = 5, total_pages after filtering = 3 --> safe_page = 3
  const safePage = Math.min(page, totalPages)

  // Return to the first run page when search or filters replace the run list.
  useEffect(() => {
    setPage(1)
  }, [runs])

  // Render only the runs belonging to the current inner page.
  const startIndex = (safePage - 1) * RUNS_PER_PAGE
  const visibleRuns = runs.slice(startIndex, startIndex + RUNS_PER_PAGE)

  return (
    <HypothesisCard
      index={hypothesisIndex}
      runCount={runs.length}
      defaultOpen={false}
    >
      {visibleRuns.map(({ steps, index: runIndex }) => (
        <RunCard index={runIndex} defaultOpen={false} key={runIndex}>
          <StepsTable steps={steps} />
        </RunCard>
      ))}

      {/* Runs pagination */}
      {totalPages > 1 && (
        <div className="d-flex justify-content-between align-items-center pt-2">
          <button
            className="btn btn-sm btn-outline-primary"
            type="button"
            disabled={safePage === 1}
            onClick={() => setPage(safePage - 1)}
          >
            Previous runs
          </button>

          <span className="small text-secondary">
            Runs {startIndex + 1}-
            {Math.min(startIndex + RUNS_PER_PAGE, runs.length)} of {runs.length}
          </span>

          <button
            className="btn btn-sm btn-outline-primary"
            type="button"
            disabled={safePage === totalPages}
            onClick={() => setPage(safePage + 1)}
          >
            Next runs
          </button>
        </div>
      )}
    </HypothesisCard>
  )
}

function Hypotheses({ hypotheses, page, onPageChange, emptyMessage = '' }) {
  // Show no hypotheses message if hypotheses is empty
  if (hypotheses.length === 0) {
    return emptyMessage ? (
      <div className="alert alert-info" role="status">
        {emptyMessage}
      </div>
    ) : null
  }

  // Hypotheses pagination
  const totalPages = Math.max(
    1,
    Math.ceil(hypotheses.length / HYPOTHESES_PER_PAGE),
  )
  const safePage = Math.min(page, totalPages)

  // Slice after filtering so pagination always reflects the visible result set.
  const startIndex = (safePage - 1) * HYPOTHESES_PER_PAGE
  const visibleHypotheses = hypotheses.slice(
    startIndex,
    startIndex + HYPOTHESES_PER_PAGE,
  )

  return (
    <>
      {visibleHypotheses.map(({ runs, index }) => (
        <PaginatedHypothesis
          runs={runs}
          hypothesisIndex={index}
          key={index}
        />
      ))}

      {/* Pagination: show when you have more than one page */}
      {totalPages > 1 && (
        <nav
          className="row g-0 align-items-center my-4"
          aria-label="Hypotheses pagination"
        >
          <div className="col-4">
            <button
              className="btn btn-outline-primary"
              type="button"
              disabled={safePage === 1}
              onClick={() => onPageChange(safePage - 1)}
            >
              Previous
            </button>
          </div>

          <span className="col-4 text-center">
            Page {safePage} of {totalPages}
          </span>

          <div className="col-4 text-end">
            <button
              className="btn btn-outline-primary"
              type="button"
              disabled={safePage === totalPages}
              onClick={() => onPageChange(safePage + 1)}
            >
              Next
            </button>
          </div>
        </nav>
      )}
    </>
  )
}

export default Hypotheses;