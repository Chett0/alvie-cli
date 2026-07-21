import type { ParsedOutput } from './types'
import { validateParsedOutput } from './validation'

const FILE_QUERY_PARAMETER = 'file'
const PARSED_OUTPUT_URL_PREFIX = '/parsed-output/'

// Keep parsing and validation identical for local imports and URL-based loading.
export const parseParsedOutput = (json: string): ParsedOutput =>
  validateParsedOutput(JSON.parse(json))

export const getParsedOutputUrl = (): string | null =>
  new URLSearchParams(window.location.search).get(FILE_QUERY_PARAMETER)

export const loadParsedOutput = async (
  fileUrl: string,
  signal?: AbortSignal,
): Promise<ParsedOutput> => {
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
