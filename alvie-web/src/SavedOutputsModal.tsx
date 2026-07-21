import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteAllStoredOutputs,
  deleteStoredOutput,
  listStoredOutputs,
  renameStoredOutput,
} from './api'
import type { StoredOutputSummary } from './api'

const OUTPUTS_PER_PAGE = 6

interface SavedOutputsModalProps {
  onClose: () => void
  onView: (id: number) => void
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

// Split a filename into its editable stem and its (non-editable) extension.
// A leading dot (e.g. ".gitignore") is treated as part of the stem.
const splitFilename = (filename: string): { stem: string; extension: string } => {
  const dotIndex = filename.lastIndexOf('.')
  if (dotIndex <= 0) {
    return { stem: filename, extension: '' }
  }
  return {
    stem: filename.slice(0, dotIndex),
    extension: filename.slice(dotIndex),
  }
}

function SavedOutputsModal({ onClose, onView }: SavedOutputsModalProps) {
  const [outputs, setOutputs] = useState<StoredOutputSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<number | 'all' | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingStem, setEditingStem] = useState('')
  const [page, setPage] = useState(1)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  const refresh = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true)
    setError('')

    try {
      const stored = await listStoredOutputs(signal)
      setOutputs(stored)
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === 'AbortError') {
        return
      }
      setError(
        loadError instanceof Error
          ? loadError.message
          : 'Unable to load saved configurations.',
      )
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void refresh(controller.signal)
    return () => controller.abort()
  }, [refresh])

  useEffect(() => {
    const previouslyFocusedElement = document.activeElement

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    document.body.classList.add('modal-open')
    document.addEventListener('keydown', closeOnEscape)
    dialogRef.current?.focus()

    return () => {
      document.body.classList.remove('modal-open')
      document.removeEventListener('keydown', closeOnEscape)

      if (previouslyFocusedElement instanceof HTMLElement) {
        previouslyFocusedElement.focus()
      }
    }
  }, [onClose])

  const totalPages = Math.max(1, Math.ceil(outputs.length / OUTPUTS_PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const startIndex = (safePage - 1) * OUTPUTS_PER_PAGE
  const visibleOutputs = useMemo(
    () => outputs.slice(startIndex, startIndex + OUTPUTS_PER_PAGE),
    [outputs, startIndex],
  )

  const removeOne = async (id: number) => {
    setBusyId(id)
    setError('')

    try {
      await deleteStoredOutput(id)
      await refresh()
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete this configuration.',
      )
    } finally {
      setBusyId(null)
    }
  }

  const startEditing = (output: StoredOutputSummary) => {
    setEditingId(output.id)
    setEditingStem(splitFilename(output.filename).stem)
    setError('')
  }

  const cancelEditing = () => {
    setEditingId(null)
    setEditingStem('')
  }

  const saveEditing = async (output: StoredOutputSummary) => {
    const { extension } = splitFilename(output.filename)
    const stem = editingStem.trim()

    if (!stem) {
      setError('The file name cannot be empty.')
      return
    }

    const nextName = `${stem}${extension}`
    if (nextName === output.filename) {
      cancelEditing()
      return
    }

    setBusyId(output.id)
    setError('')

    try {
      await renameStoredOutput(output.id, nextName)
      cancelEditing()
      await refresh()
    } catch (renameError) {
      setError(
        renameError instanceof Error
          ? renameError.message
          : 'Unable to rename this configuration.',
      )
    } finally {
      setBusyId(null)
    }
  }

  const removeAll = async () => {
    if (!window.confirm('Delete all saved configurations? This cannot be undone.')) {
      return
    }

    setBusyId('all')
    setError('')

    try {
      await deleteAllStoredOutputs()
      setPage(1)
      await refresh()
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete the configurations.',
      )
    } finally {
      setBusyId(null)
    }
  }

  const isBusy = busyId !== null

  return (
    <>
      <div
        className="modal d-block"
        role="dialog"
        aria-modal="true"
        aria-labelledby="saved-outputs-title"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) onClose()
        }}
      >
        <div className="modal-dialog modal-dialog-centered modal-lg">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="saved-outputs-title">
                Saved configurations
              </h5>
              <button
                type="button"
                className="btn-close"
                aria-label="Close"
                onClick={onClose}
                disabled={isBusy}
              />
            </div>

            <div className="modal-body">
              {isLoading ? (
                <div className="text-secondary text-center py-4">
                  Loading saved configurations…
                </div>
              ) : outputs.length === 0 ? (
                <div className="text-secondary text-center py-4">
                  No saved configurations yet.
                </div>
              ) : (
                <div className="list-group">
                  {visibleOutputs.map((output) => {
                    const { extension } = splitFilename(output.filename)
                    const isEditing = editingId === output.id

                    return (
                      <div
                        key={output.id}
                        className="list-group-item d-flex justify-content-between align-items-center gap-3"
                      >
                        {isEditing ? (
                          <form
                            className="d-flex align-items-center gap-2 flex-grow-1"
                            onSubmit={(event) => {
                              event.preventDefault()
                              void saveEditing(output)
                            }}
                          >
                            <div className="input-group input-group-sm flex-grow-1">
                              <input
                                type="text"
                                className="form-control"
                                value={editingStem}
                                onChange={(event) =>
                                  setEditingStem(event.target.value)
                                }
                                onKeyDown={(event) => {
                                  if (event.key === 'Escape') cancelEditing()
                                }}
                                disabled={busyId === output.id}
                                aria-label="File name"
                                // eslint-disable-next-line jsx-a11y/no-autofocus
                                autoFocus
                              />
                              {extension && (
                                <span className="input-group-text">{extension}</span>
                              )}
                            </div>

                            <button
                              type="submit"
                              className="btn btn-sm btn-outline-success d-inline-flex align-items-center"
                              disabled={busyId === output.id}
                              aria-label="Save file name"
                              title="Save"
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                fill="currentColor"
                                viewBox="0 0 16 16"
                                aria-hidden="true"
                              >
                                <path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0Z" />
                              </svg>
                            </button>

                            <button
                              type="button"
                              className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center"
                              onClick={cancelEditing}
                              disabled={busyId === output.id}
                              aria-label="Cancel rename"
                              title="Cancel"
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                width="16"
                                height="16"
                                fill="currentColor"
                                viewBox="0 0 16 16"
                                aria-hidden="true"
                              >
                                <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708Z" />
                              </svg>
                            </button>
                          </form>
                        ) : (
                          <>
                            <button
                              type="button"
                              className="btn btn-link text-start text-decoration-none p-0 flex-grow-1"
                              onClick={() => onView(output.id)}
                              disabled={isBusy}
                            >
                              <span className="d-block fw-semibold text-body">
                                {output.filename}
                              </span>
                              <span className="d-block small text-secondary">
                                {output.executable} · {formatDate(output.created_at)}
                              </span>
                            </button>

                            <div className="d-flex align-items-center gap-2">
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center"
                                onClick={() => startEditing(output)}
                                disabled={isBusy}
                                aria-label={`Rename ${output.filename}`}
                                title="Rename"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  width="16"
                                  height="16"
                                  fill="currentColor"
                                  viewBox="0 0 16 16"
                                  aria-hidden="true"
                                >
                                  <path d="M12.146.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1 0 .708l-10 10a.5.5 0 0 1-.168.11l-5 2a.5.5 0 0 1-.65-.65l2-5a.5.5 0 0 1 .11-.168l10-10ZM11.207 2.5 13.5 4.793 14.793 3.5 12.5 1.207 11.207 2.5Zm1.586 3L10.5 3.207 4 9.707V10h.5a.5.5 0 0 1 .5.5v.5h.5a.5.5 0 0 1 .5.5v.5h.293l6.5-6.5Zm-9.761 5.175-.106.106-1.528 3.821 3.821-1.528.106-.106A.5.5 0 0 1 5 12.5V12h-.5a.5.5 0 0 1-.5-.5V11h-.5a.5.5 0 0 1-.468-.325Z" />
                                </svg>
                              </button>

                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger d-inline-flex align-items-center"
                                onClick={() => void removeOne(output.id)}
                                disabled={isBusy}
                                aria-label={`Delete ${output.filename}`}
                                title="Delete"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  width="16"
                                  height="16"
                                  fill="currentColor"
                                  viewBox="0 0 16 16"
                                  aria-hidden="true"
                                >
                                  <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6Z" />
                                  <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1ZM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118ZM2.5 3h11V2h-11v1Z" />
                                </svg>
                              </button>
                            </div>
                          </>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {error && (
                <div className="alert alert-danger mt-3 mb-0" role="alert">
                  {error}
                </div>
              )}

              {totalPages > 1 && (
                <nav
                  className="row g-0 align-items-center mt-3"
                  aria-label="Saved configurations pagination"
                >
                  <div className="col-4">
                    <button
                      className="btn btn-sm btn-outline-primary"
                      type="button"
                      disabled={safePage === 1 || isBusy}
                      onClick={() => setPage(safePage - 1)}
                    >
                      Previous
                    </button>
                  </div>

                  <span className="col-4 text-center small text-secondary">
                    Page {safePage} of {totalPages}
                  </span>

                  <div className="col-4 text-end">
                    <button
                      className="btn btn-sm btn-outline-primary"
                      type="button"
                      disabled={safePage === totalPages || isBusy}
                      onClick={() => setPage(safePage + 1)}
                    >
                      Next
                    </button>
                  </div>
                </nav>
              )}
            </div>

            <div className="modal-footer justify-content-between">
              <button
                type="button"
                className="btn btn-outline-danger"
                onClick={() => void removeAll()}
                disabled={isBusy || outputs.length === 0}
              >
                {busyId === 'all' ? 'Deleting…' : 'Delete all'}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={onClose}
                disabled={isBusy}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  )
}

export default SavedOutputsModal
