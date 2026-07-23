import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteAllStoredOutputs,
  deleteStoredOutput,
  downloadStoredOutput,
  listStoredOutputs,
  renameStoredOutput,
} from './api'
import type { StoredOutputSummary } from './api'
import Spinner from './Spinner'

const OUTPUTS_PER_PAGE = 6

interface SavedOutputsModalProps {
  currentOutputId: number | null
  onClose: () => void
  onView: (id: number) => void
}

type PendingDelete =
  | { type: 'one'; output: StoredOutputSummary }
  | { type: 'all' }
  | null

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

function SavedOutputsModal({
  currentOutputId,
  onClose,
  onView,
}: SavedOutputsModalProps) {
  const [outputs, setOutputs] = useState<StoredOutputSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<number | 'all' | `download-${number}` | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingStem, setEditingStem] = useState('')
  const [page, setPage] = useState(1)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  const [pendingDelete, setPendingDelete] = useState<PendingDelete>(null)
  const isBusy = busyId !== null

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
          : 'Unable to load saved executions.',
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
      if (event.key !== 'Escape') return

      if (pendingDelete) {
        if (!isBusy) setPendingDelete(null)
        return
      }

      onClose()
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
  }, [isBusy, onClose, pendingDelete])

  const totalPages = Math.max(1, Math.ceil(outputs.length / OUTPUTS_PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const startIndex = (safePage - 1) * OUTPUTS_PER_PAGE
  const visibleOutputs = useMemo(
    () => outputs.slice(startIndex, startIndex + OUTPUTS_PER_PAGE),
    [outputs, startIndex],
  )

  const removeOne = async (id: number): Promise<boolean> => {
    setBusyId(id)
    setError('')

    try {
      await deleteStoredOutput(id)
      await refresh()
      return true
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete this configuration.',
      )
      return false
    } finally {
      setBusyId(null)
    }
  }

  const requestRemoveOne = (output: StoredOutputSummary) => {
    setPendingDelete({ type: 'one', output })
    setError('')
  }

  const downloadOne = async (output: StoredOutputSummary) => {
    const busyKey = `download-${output.id}` as const
    setBusyId(busyKey)
    setError('')

    try {
      const { filename, data } = await downloadStoredOutput(output.id)
      const blob = new Blob([`${JSON.stringify(data, null, 2)}\n`], {
        type: 'application/json',
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.append(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (downloadError) {
      setError(
        downloadError instanceof Error
          ? downloadError.message
          : 'Unable to download this configuration.',
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

  const removeAll = async (): Promise<boolean> => {
    setBusyId('all')
    setError('')

    try {
      await deleteAllStoredOutputs()
      setPage(1)
      await refresh()
      return true
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete the configurations.',
      )
      return false
    } finally {
      setBusyId(null)
    }
  }

  const confirmDelete = async () => {
    if (!pendingDelete) return

    const shouldRedirect =
      pendingDelete.type === 'all' ||
      pendingDelete.output.id === currentOutputId
    const deleted =
      pendingDelete.type === 'one'
        ? await removeOne(pendingDelete.output.id)
        : await removeAll()

    if (!deleted) return

    setPendingDelete(null)
    if (shouldRedirect) window.location.assign('/')
  }

  const cancelDelete = () => {
    if (isBusy) return
    setPendingDelete(null)
  }

  const deleteTitle =
    pendingDelete?.type === 'all'
      ? 'Delete all saved executions?'
      : 'Delete saved execution?'
  const deleteMessage =
    pendingDelete?.type === 'all'
      ? 'This will permanently remove every saved execution from the database.'
      : `This will permanently remove "${pendingDelete?.output.filename ?? ''}" from the database.`

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
                Saved executions
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
                <div className="d-flex flex-column align-items-center text-secondary text-center py-4 gap-2">
                  <Spinner label="Loading saved executions…" />
                  <span>Loading saved executions…</span>
                </div>
              ) : outputs.length === 0 ? (
                <div className="text-secondary text-center py-4">
                  No saved executions yet.
                </div>
              ) : (
                <div className="list-group">
                  {visibleOutputs.map((output) => {
                    const { extension } = splitFilename(output.filename)
                    const isEditing = editingId === output.id

                    return (
                      <div
                        key={output.id}
                        className="saved-output-item list-group-item d-flex justify-content-between align-items-center gap-3"
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
                              {busyId === output.id ? (
                                <Spinner size="sm" variant="success" label="Saving…" />
                              ) : (
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
                              )}
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
                                onClick={() => void downloadOne(output)}
                                disabled={isBusy}
                                aria-label={`Download ${output.filename}`}
                                title="Download"
                              >
                                {busyId === `download-${output.id}` ? (
                                  <Spinner size="sm" variant="secondary" label="Downloading…" />
                                ) : (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    width="16"
                                    height="16"
                                    fill="currentColor"
                                    viewBox="0 0 16 16"
                                    aria-hidden="true"
                                  >
                                    <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5A1.5 1.5 0 0 0 2.5 14h11a1.5 1.5 0 0 0 1.5-1.5v-2.5a.5.5 0 0 1 1 0v2.5A2.5 2.5 0 0 1 13.5 15h-11A2.5 2.5 0 0 1 0 12.5v-2.5a.5.5 0 0 1 .5-.5Z" />
                                    <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3Z" />
                                  </svg>
                                )}
                              </button>

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
                                onClick={() => requestRemoveOne(output)}
                                disabled={isBusy}
                                aria-label={`Delete ${output.filename}`}
                                title="Delete"
                              >
                                {busyId === output.id ? (
                                  <Spinner size="sm" variant="danger" label="Deleting…" />
                                ) : (
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
                                )}
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
                  aria-label="Saved executions pagination"
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
                className="btn btn-outline-danger d-inline-flex align-items-center gap-2"
                onClick={() => setPendingDelete({ type: 'all' })}
                disabled={isBusy || outputs.length === 0}
              >
                {busyId === 'all' && (
                  <Spinner size="sm" variant="danger" label="Deleting…" />
                )}
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
      {pendingDelete && (
        <div
          className="modal d-block"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-confirm-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) cancelDelete()
          }}
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow rounded-4">
              <div className="modal-body text-center px-4 py-4">
                <div className="d-inline-flex align-items-center justify-content-center rounded-circle bg-danger-subtle text-danger mb-3 p-3">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="28"
                    height="28"
                    fill="currentColor"
                    viewBox="0 0 16 16"
                    aria-hidden="true"
                  >
                    <path d="M7.938 2.016A.13.13 0 0 1 8.002 2a.13.13 0 0 1 .063.016.15.15 0 0 1 .054.057l6.857 11.667c.036.061.035.114.016.15a.16.16 0 0 1-.13.085H1.142a.16.16 0 0 1-.13-.085c-.02-.036-.02-.089.016-.15L7.884 2.073a.15.15 0 0 1 .054-.057Zm1.044-.45a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566Z" />
                    <path d="M7.002 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0ZM7.1 5.995a.905.905 0 1 1 1.8 0l-.35 3.507a.553.553 0 0 1-1.1 0L7.1 5.995Z" />
                  </svg>
                </div>

                <h5 className="modal-title fw-bold mb-3" id="delete-confirm-title">
                  {deleteTitle}
                </h5>
                <p className="mb-4 text-secondary">{deleteMessage}</p>
                <p className="visually-hidden">
                  This action cannot be undone.
                </p>

                <button
                  type="button"
                  className="btn btn-danger btn-lg w-100 d-inline-flex align-items-center justify-content-center gap-2 mb-3"
                  onClick={() => void confirmDelete()}
                  disabled={isBusy}
                >
                  {isBusy && <Spinner size="sm" variant="light" label="Deleting..." />}
                  {isBusy ? 'Deleting...' : 'Delete'}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary btn-lg w-100"
                  onClick={cancelDelete}
                  disabled={isBusy}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="modal-backdrop fade show" />
      {pendingDelete && <div className="modal-backdrop fade show" />}
    </>
  )
}

export default SavedOutputsModal
