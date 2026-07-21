import type { ParsedOutput } from './types'
import { validateParsedOutput } from './validation'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/+$/, '')

export interface StoredOutputSummary {
  id: number
  filename: string
  executable: string
  start: string
  end: string
  created_at: string
}

interface StoredOutputResponse {
  id: number
  filename: string
  created_at: string
  data: unknown
}

export const listStoredOutputs = async (
  signal?: AbortSignal,
): Promise<StoredOutputSummary[]> => {
  const response = await fetch(`${API_BASE_URL}/api/outputs`, { signal })

  if (!response.ok) {
    throw new Error(`Unable to load stored outputs (${response.status}).`)
  }

  return (await response.json()) as StoredOutputSummary[]
}

export const fetchStoredOutput = async (
  id: number | string,
  signal?: AbortSignal,
): Promise<ParsedOutput> => {
  const response = await fetch(`${API_BASE_URL}/api/outputs/${id}`, { signal })

  if (response.status === 404) {
    throw new Error(`Stored output ${id} was not found.`)
  }
  if (!response.ok) {
    throw new Error(`Unable to load stored output ${id} (${response.status}).`)
  }

  const record = (await response.json()) as StoredOutputResponse
  return validateParsedOutput(record.data)
}

export const renameStoredOutput = async (
  id: number | string,
  filename: string,
  signal?: AbortSignal,
): Promise<StoredOutputSummary> => {
  const response = await fetch(`${API_BASE_URL}/api/outputs/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename }),
    signal,
  })

  if (response.status === 404) {
    throw new Error(`Stored output ${id} was not found.`)
  }
  if (!response.ok) {
    throw new Error(`Unable to rename stored output ${id} (${response.status}).`)
  }

  return (await response.json()) as StoredOutputSummary
}

export const deleteStoredOutput = async (
  id: number | string,
  signal?: AbortSignal,
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/outputs/${id}`, {
    method: 'DELETE',
    signal,
  })

  if (response.status === 404) {
    throw new Error(`Stored output ${id} was not found.`)
  }
  if (!response.ok) {
    throw new Error(`Unable to delete stored output ${id} (${response.status}).`)
  }
}

// Delete every stored output (DELETE /api/outputs).
export const deleteAllStoredOutputs = async (
  signal?: AbortSignal,
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/api/outputs`, {
    method: 'DELETE',
    signal,
  })

  if (!response.ok) {
    throw new Error(`Unable to delete stored outputs (${response.status}).`)
  }
}
