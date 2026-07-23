import { fetchStoredOutput } from './api'
import type { ParsedOutput } from './types'
import { validateParsedOutput } from './validation'

const FILE_QUERY_PARAMETER = 'file'

// Keep parsing and validation identical for local imports and URL-based loading.
export const parseParsedOutput = (json: string): ParsedOutput =>
  validateParsedOutput(JSON.parse(json))

export const getParsedOutputUrl = (): string | null =>
  new URLSearchParams(window.location.search).get(FILE_QUERY_PARAMETER)

// A `file` value must be a stored output's backend id (e.g. ?file=3).
const isStoredOutputId = (value: string): boolean => /^\d+$/.test(value)

export const loadParsedOutput = async (
  fileUrl: string,
  signal?: AbortSignal,
): Promise<ParsedOutput> => {
  if (!isStoredOutputId(fileUrl)) {
    throw new Error('The file URL must be a stored output id.')
  }

  return fetchStoredOutput(fileUrl, signal)
}

// Point the shareable ?file= link at a stored output's backend id.
export const setStoredOutputUrl = (id: number | string): void => {
  const url = new URL(window.location.href)

  url.searchParams.set(FILE_QUERY_PARAMETER, String(id))
  window.history.replaceState(null, '', url)
}
