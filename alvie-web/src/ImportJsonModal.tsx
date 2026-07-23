import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'

interface ImportJsonModalProps {
  onClose: () => void
  onImport: (file: File, saveToDatabase: boolean) => Promise<void>
}

function ImportJsonModal({ onClose, onImport }: ImportJsonModalProps) {
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const dragDepthRef = useRef(0)

  useEffect(() => {
    const previouslyFocusedElement = document.activeElement

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return

      if (pendingFile) {
        if (!isImporting) setPendingFile(null)
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
  }, [isImporting, onClose, pendingFile])

  const requestImport = (file?: File) => {
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.json')) {
      setError('Please select a JSON file.')
      return
    }

    setError('')
    setPendingFile(file)
  }

  const importFile = async (saveToDatabase: boolean) => {
    if (!pendingFile) return

    setIsImporting(true)

    try {
      await onImport(pendingFile, saveToDatabase)
      onClose()
    } catch (importError) {
      setError(
        importError instanceof Error
          ? importError.message
          : 'Unable to import this JSON file.',
      )
      setIsImporting(false)
      setPendingFile(null)
    }
  }

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    requestImport(file)
  }

  // Route both browsing and drag-and-drop through the same import path.
  const dropFile = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    dragDepthRef.current = 0
    setIsDragging(false)
    requestImport(event.dataTransfer.files?.[0]) // take first dropped file
  }

  return (
    <>
      <div
        className="modal d-block"
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-json-title"
        ref={dialogRef}
        tabIndex={-1}
        onMouseDown={(event) => {
          if (event.target === event.currentTarget) onClose()
        }}
      >
        <div className="modal-dialog modal-dialog-centered">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="import-json-title">
                Import parsed output
              </h5>
              <button
                type="button"
                className="btn-close"
                aria-label="Close"
                onClick={onClose}
                disabled={isImporting}
              />
            </div>

            <div className="modal-body">
              <button
                type="button"
                className={`import-drop-zone w-100 rounded-3 p-5 ${
                  isDragging ? 'is-dragging' : ''
                }`}
                onClick={() => fileInputRef.current?.click()}
                onDragEnter={(event) => {
                  event.preventDefault()
                  dragDepthRef.current += 1
                  setIsDragging(true)
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={(event) => {
                  event.preventDefault()
                  dragDepthRef.current = Math.max(0, dragDepthRef.current - 1)
                  if (dragDepthRef.current === 0) setIsDragging(false)
                }}
                onDrop={dropFile}
                disabled={isImporting}
              >
                <span className="d-block fw-semibold mb-1">
                  {isImporting ? 'Importing…' : 'Choose a JSON file'}
                </span>
                <span className="d-block small text-secondary">
                  Click to browse or drag and drop it here
                </span>
              </button>

              <input
                className="d-none"
                type="file"
                accept="application/json,.json"
                onChange={selectFile}
                ref={fileInputRef}
              />

              {error && (
                <div className="alert alert-danger mt-3 mb-0" role="alert">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      {pendingFile && (
        <div
          className="modal d-block"
          role="dialog"
          aria-modal="true"
          aria-labelledby="save-import-title"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isImporting) {
              setPendingFile(null)
            }
          }}
        >
          <div className="modal-dialog modal-dialog-centered modal-sm">
            <div className="modal-content border-0 shadow rounded-4">
              <div className="modal-body text-center px-4 py-4">
                <h6 className="modal-title fw-bold mb-2" id="save-import-title">
                  Save this configuration?
                </h6>
                <p className="mb-4 small text-secondary">
                  Store {pendingFile.name} in the database for later access.
                </p>

                <button
                  type="button"
                  className="btn btn-primary w-100 d-inline-flex align-items-center justify-content-center gap-2 mb-2"
                  onClick={() => void importFile(true)}
                  disabled={isImporting}
                >
                  {isImporting && <span className="spinner-border spinner-border-sm" />}
                  {isImporting ? 'Saving...' : 'Save'}
                </button>

                <button
                  type="button"
                  className="btn btn-outline-secondary w-100"
                  onClick={() => void importFile(false)}
                  disabled={isImporting}
                >
                  Do not save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      <div className="modal-backdrop fade show" />
      {pendingFile && <div className="modal-backdrop fade show" />}
    </>
  )
}

export default ImportJsonModal
