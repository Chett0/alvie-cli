import { useCallback, useEffect, useState } from 'react'
import {
  deleteStoredOutput,
  downloadStoredOutput,
  listStoredOutputs,
  renameStoredOutput,
} from './api'
import type { StoredOutputSummary } from './api'
import Spinner from './Spinner'

interface SavedOutputsHomeProps {
  onView: (id: number) => void
}

const formatDate = (value: string): string => {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

const splitFilename = (filename: string): { stem: string; extension: string } => {
  const dotIndex = filename.lastIndexOf('.')
  if (dotIndex <= 0) return { stem: filename, extension: '' }
  return {
    stem: filename.slice(0, dotIndex),
    extension: filename.slice(dotIndex),
  }
}

function SavedOutputsHome({ onView }: SavedOutputsHomeProps) {
  const [outputs, setOutputs] = useState<StoredOutputSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<number | `download-${number}` | null>(null)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingStem, setEditingStem] = useState('')
  const [pendingDelete, setPendingDelete] = useState<StoredOutputSummary | null>(null)
  const isBusy = busyId !== null

  const loadOutputs = useCallback(async (signal?: AbortSignal) => {
    setIsLoading(true)
    setError('')

    try {
      setOutputs(await listStoredOutputs(signal))
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
    void loadOutputs(controller.signal)
    return () => controller.abort()
  }, [loadOutputs])

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

  const saveEditing = async (output: StoredOutputSummary) => {
    const stem = editingStem.trim()
    if (!stem) {
      setError('The file name cannot be empty.')
      return
    }

    const nextName = `${stem}${splitFilename(output.filename).extension}`
    if (nextName === output.filename) {
      setEditingId(null)
      return
    }

    setBusyId(output.id)
    setError('')

    try {
      await renameStoredOutput(output.id, nextName)
      setEditingId(null)
      await loadOutputs()
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

  const deleteOne = async (output: StoredOutputSummary) => {
    setBusyId(output.id)
    setError('')

    try {
      await deleteStoredOutput(output.id)
      await loadOutputs()
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : 'Unable to delete this configuration.',
      )
    } finally {
      setBusyId(null)
      setPendingDelete(null)
    }
  }

  return (
    <div className="bg-white border rounded-3 p-4">
      <div className="d-flex justify-content-between align-items-center gap-3 mb-3">
        <div>
          <h5 className="mb-1">Saved executions</h5>
          <p className="mb-0 small text-secondary">
            Open a parsed output saved in the database.
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="d-flex flex-column align-items-center text-secondary py-4 gap-2">
          <Spinner label="Loading saved executions..." />
          <span>Loading saved executions...</span>
        </div>
      ) : error ? (
        <div className="alert alert-danger mb-0" role="alert">
          {error}
        </div>
      ) : outputs.length === 0 ? (
        <div className="text-secondary text-center py-4">
          No saved executions yet.
        </div>
      ) : (
        <div className="list-group">
          {outputs.map((output) => {
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
                        onChange={(event) => setEditingStem(event.target.value)}
                        disabled={busyId === output.id}
                        aria-label="File name"
                        autoFocus
                      />
                      {extension && <span className="input-group-text">{extension}</span>}
                    </div>

                    <button
                      type="submit"
                      className="btn btn-sm btn-outline-success"
                      disabled={busyId === output.id}
                    >
                      Save
                    </button>

                    <button
                      type="button"
                      className="btn btn-sm btn-outline-secondary"
                      onClick={() => setEditingId(null)}
                      disabled={busyId === output.id}
                    >
                      Cancel
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
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => void downloadOne(output)}
                        disabled={isBusy}
                        title="Download"
                      >
                        {busyId === `download-${output.id}` ? '...' : 'Download'}
                      </button>

                      <button
                        type="button"
                        className="btn btn-sm btn-outline-secondary"
                        onClick={() => startEditing(output)}
                        disabled={isBusy}
                      >
                        Edit
                      </button>

                      <button
                        type="button"
                        className="btn btn-sm btn-outline-danger"
                        onClick={() => setPendingDelete(output)}
                        disabled={isBusy}
                      >
                        {busyId === output.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      )}

      {pendingDelete && (
        <>
          <div
            className="modal d-block"
            role="dialog"
            aria-modal="true"
            aria-labelledby="home-delete-title"
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

                  <h5 className="modal-title fw-bold mb-3" id="home-delete-title">
                    Delete saved configuration?
                  </h5>
                  <p className="mb-4 text-secondary">
                    This will permanently remove "{pendingDelete.filename}" from the database.
                  </p>

                  <button
                    type="button"
                    className="btn btn-danger btn-lg w-100 mb-3"
                    onClick={() => void deleteOne(pendingDelete)}
                    disabled={isBusy}
                  >
                    {isBusy ? 'Deleting...' : 'Delete'}
                  </button>

                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-lg w-100"
                    onClick={() => setPendingDelete(null)}
                    disabled={isBusy}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" />
        </>
      )}
    </div>
  )
}

export default SavedOutputsHome
