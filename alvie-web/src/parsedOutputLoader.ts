import { fetchStoredOutput } from './api'
import type { ParsedOutput } from './types'
import { validateParsedOutput } from './validation'

const FILE_QUERY_PARAMETER = 'file'
const PARSED_OUTPUT_URL_PREFIX = '/parsed-output/'

// Keep parsing and validation identical for local imports and URL-based loading.
export const parseParsedOutput = (json: string): ParsedOutput =>
  validateParsedOutput(JSON.parse(json))

export const getParsedOutputUrl = (): string | null =>
  new URLSearchParams(window.location.search).get(FILE_QUERY_PARAMETER)

// A `file` value made up solely of digits is treated as a stored output's
// backend id (e.g. ?file=3); anything else is a /parsed-output/ path.
const isStoredOutputId = (value: string): boolean => /^\d+$/.test(value)

export const loadParsedOutput = async (
  fileUrl: string,
  signal?: AbortSignal,
): Promise<ParsedOutput> => {
  // Load from the backend when the link carries a stored output id.
  if (isStoredOutputId(fileUrl)) {
    return fetchStoredOutput(fileUrl, signal)
  }

  const url = new URL(fileUrl, window.location.origin)

  // Parsed outputs must come from the read-only directory served by the viewer.
  if (
    url.origin !== window.location.origin ||
    !url.pathname.startsWith(PARSED_OUTPUT_URL_PREFIX)
  ) {
    throw new Error(
      `The file URL must start with "${PARSED_OUTPUT_URL_PREFIX}".`,
    )
  }

  const response = await fetch(url, { signal })
  if (!response.ok) {
    throw new Error(`Unable to load ${url.pathname} (${response.status}).`)
  }

  return parseParsedOutput(await response.text())
}

export const setParsedOutputUrl = (fileName: string): void => {
  const url = new URL(window.location.href)
  const fileUrl = `${PARSED_OUTPUT_URL_PREFIX}${encodeURIComponent(fileName)}`

  url.searchParams.set(FILE_QUERY_PARAMETER, fileUrl)
  window.history.replaceState(null, '', url)
}

// Point the shareable ?file= link at a stored output's backend id.
export const setStoredOutputUrl = (id: number | string): void => {
  const url = new URL(window.location.href)

  url.searchParams.set(FILE_QUERY_PARAMETER, String(id))
  window.history.replaceState(null, '', url)
}
