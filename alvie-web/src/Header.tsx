interface HeaderProps {
  isHome: boolean
  onHomeClick: () => void
  onImportClick: () => void
  onSavedClick: () => void
}

function Header({
  isHome,
  onHomeClick,
  onImportClick,
  onSavedClick,
}: HeaderProps) {
  return (
    <header className="container-fluid">
      <div className="d-flex justify-content-between align-items-center p-3">
        <button
          type="button"
          className="btn btn-link text-white text-decoration-none p-0"
          onClick={onHomeClick}
        >
          <h4 className="mb-0">AlvieWeb</h4>
        </button>

        <div className="d-inline-flex align-items-center gap-2">
          {!isHome && (
            <button
              className="btn btn-primary d-inline-flex align-items-center justify-content-center gap-2"
              style={{ minWidth: '9.5rem' }}
              type="button"
              onClick={onSavedClick}
            >
              {/* Saved configurations ICON */}
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                fill="currentColor"
                viewBox="0 0 16 16"
                aria-hidden="true"
              >
                <path d="M2.5 3.5a.5.5 0 0 1 0-1h11a.5.5 0 0 1 0 1zm2-2a.5.5 0 0 1 0-1h7a.5.5 0 0 1 0 1zM0 13a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 16 13V6a1.5 1.5 0 0 0-1.5-1.5h-13A1.5 1.5 0 0 0 0 6zm1.5.5A.5.5 0 0 1 1 13V6a.5.5 0 0 1 .5-.5h13a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-.5.5z" />
              </svg>
              Saved
            </button>
          )}

          <button
            className="btn btn-primary d-inline-flex align-items-center justify-content-center gap-2"
            style={{ minWidth: '9.5rem' }}
            type="button"
            onClick={onImportClick}
          >
            {/* Import ICON */}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              fill="currentColor"
              viewBox="0 0 16 16"
              aria-hidden="true"
            >
              <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5" />
              <path d="M7.646.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 1.707V11.5a.5.5 0 0 1-1 0V1.707L5.354 3.854a.5.5 0 1 1-.708-.708z" />
            </svg>
            Import JSON
          </button>
        </div>
      </div>
    </header>
  )
}

export default Header
