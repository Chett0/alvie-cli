import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent } from 'react'

interface ImportJsonModalProps {
  onClose: () => void
  onImport: (file: File) => Promise<void>
}

function ImportJsonModal({ onClose, onImport }: ImportJsonModalProps) {
  const [error, setError] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [isImporting, setIsImporting] = useState(false)
  const dialogRef = useRef<HTMLDivElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

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

  const importFile = async (file?: File) => {
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.json')) {
      setError('Please select a JSON file.')
      return
    }

    setError('')
    setIsImporting(true)

    try {
      await onImport(file)
      onClose()
    } catch (importError) {
      setError(
        importError instanceof Error
          ? importError.message
          : 'Unable to import this JSON file.',
      )
      setIsImporting(false)
    }
  }

  const selectFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ''
    void importFile(file)
  }

  // Route both browsing and drag-and-drop through the same import path.
  const dropFile = (event: DragEvent<HTMLButtonElement>) => {
    event.preventDefault()
    setIsDragging(false)
    void importFile(event.dataTransfer.files?.[0])
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
                  setIsDragging(true)
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
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
      <div className="modal-backdrop fade show" />
    </>
  )
}

export default ImportJsonModal
