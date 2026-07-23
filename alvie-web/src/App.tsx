import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import './App.css'
import { filterHypotheses, indexHypotheses, symbolsToOptions } from './util'
import CommandRun from './CommandRun'
import SummaryStats from './SummaryStats'
import FilterBar from './FilterBar'
import Header from './Header'
import Hypotheses from './Hypotheses'
import ImportJsonModal from './ImportJsonModal'
import SavedOutputsHome from './SavedOutputsHome'
import SavedOutputsModal from './SavedOutputsModal'
import Spinner from './Spinner'
import { createStoredOutput, fetchStoredOutput } from './api'
import symbolCatalog from './symbolCatalog'
import {
  getParsedOutputUrl,
  loadParsedOutput,
  parseParsedOutput,
  setStoredOutputUrl,
} from './parsedOutputLoader'
import type { FilterOptions, FilterValues, ParsedOutput } from './types'

const EMPTY_HYPOTHESES: ParsedOutput['hypotheses'] = []
const EMPTY_FILTERS: FilterValues = {
  actors: [],
  inputs: [],
  outputs: [],
}

const FILTER_OPTIONS: FilterOptions = {
  actors: [
    { value: 'Attacker', label: 'Attacker' },
    { value: 'Enclave', label: 'Enclave' },
    { value: 'No actor', label: 'No actor' },
  ],
  inputs: symbolsToOptions(symbolCatalog.inputs),
  outputs: symbolsToOptions(symbolCatalog.outputs),
}

const getCurrentStoredOutputId = (): number | null => {
  const fileUrl = getParsedOutputUrl()
  if (!fileUrl || !/^\d+$/.test(fileUrl)) return null
  return Number(fileUrl)
}

function App() {
  const [parsedOutput, setParsedOutput] = useState<ParsedOutput | null>(null)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [isSavedModalOpen, setIsSavedModalOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const [loadError, setLoadError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const hypotheses = parsedOutput?.hypotheses ?? EMPTY_HYPOTHESES

  const showParsedOutput = (data: ParsedOutput) => {
    setParsedOutput(data)
    setSearch('')
    setFilters(EMPTY_FILTERS)
    setPage(1)
    setLoadError('')
  }

  const goHome = () => {
    setParsedOutput(null)
    setSearch('')
    setFilters(EMPTY_FILTERS)
    setPage(1)
    setLoadError('')
    setIsSavedModalOpen(false)
    window.history.replaceState(null, '', '/')
  }

  useEffect(() => {
    const fileUrl = getParsedOutputUrl()
    if (!fileUrl) return

    const controller = new AbortController()

    setIsLoading(true)
    void loadParsedOutput(fileUrl, controller.signal)
      .then(showParsedOutput)
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setLoadError(
          error instanceof Error ? error.message : 'Unable to load the JSON file.',
        )
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false)
      })

    return () => controller.abort()
  }, [])

  // show current results, while searching 
  const deferredSearch = useDeferredValue(search.trim())

  const { searchRegex, searchError } = useMemo(() => {
    if (!deferredSearch) return { searchRegex: null, searchError: '' }

    try {
      return {
        searchRegex: new RegExp(deferredSearch, 'i'),
        searchError: '',
      }
    } catch (error) {
      const reason =
        error instanceof Error ? error.message.split(': ').at(-1) : ''

      return {
        searchRegex: null,
        searchError: `Invalid regular expression. ${reason || ''}`,
      }
    }
  }, [deferredSearch])

  const onFilterChange = <K extends keyof FilterValues>(
    filter: K,                // filter name
    values: FilterValues[K],  // type of filter values (array of strings)
  ) => {
    setFilters((current) => ({ ...current, [filter]: values }))
    setPage(1)
  }

  const importJson = async (file: File, saveToDatabase: boolean) => {
    const data = parseParsedOutput(await file.text())
    showParsedOutput(data)

    if (saveToDatabase) {
      const stored = await createStoredOutput(file.name, data)
      setStoredOutputUrl(stored.id)
    } else {
      window.history.replaceState(null, '', '/')
    }
  }

  // Load a stored configuration from the backend and show it in the viewer.
  const viewStoredOutput = async (id: number) => {
    setIsSavedModalOpen(false)
    setIsLoading(true)
    try {
      const data = await fetchStoredOutput(id)
      showParsedOutput(data)
      setStoredOutputUrl(id)
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : 'Unable to load the configuration.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  const indexedHypotheses = useMemo(
    () => indexHypotheses(hypotheses),
    [hypotheses],
  )

  const filteredHypotheses = useMemo(
    () =>
      searchError
        ? []
        : filterHypotheses(indexedHypotheses, filters, searchRegex),
    [filters, indexedHypotheses, searchError, searchRegex],
  )

  const emptyHypothesesMessage = searchError
    ? ''
    : indexedHypotheses.length === 0
      ? 'The imported file contains no hypotheses.'
      : 'No hypotheses match the current search and filters.'

  return (
    <>
      <Header
        isHome={!parsedOutput && !loadError && !isLoading}
        onHomeClick={goHome}
        onImportClick={() => setIsImportModalOpen(true)}
        onSavedClick={() => setIsSavedModalOpen(true)}
      />

      {isImportModalOpen && (
        <ImportJsonModal
          onClose={() => setIsImportModalOpen(false)}
          onImport={importJson}
        />
      )}

      {isSavedModalOpen && (
        <SavedOutputsModal
          currentOutputId={getCurrentStoredOutputId()}
          onClose={() => setIsSavedModalOpen(false)}
          onView={(id) => void viewStoredOutput(id)}
        />
      )}

      <section className="container-fluid my-3">
        {isLoading ? (
          <div className="bg-white border rounded-3 d-flex flex-column align-items-center text-secondary py-5 px-3 gap-3">
            <Spinner label="Loading parsed output…" />
            <span>Loading parsed output…</span>
          </div>
        ) : !parsedOutput ? (
          loadError ? (
            <div className="bg-white border rounded-3 text-center py-5 px-3">
              <div className="text-danger">{loadError}</div>
            </div>
          ) : (
            <SavedOutputsHome onView={(id) => void viewStoredOutput(id)} />
          )
        ) : (
          <>
            <CommandRun
              key={parsedOutput.start}
              executable={parsedOutput.executable}
              args={parsedOutput.args}
              start={parsedOutput.start}
              end={parsedOutput.end}
            />

            <SummaryStats recap={parsedOutput.recap} />

            <FilterBar
              options={FILTER_OPTIONS}
              values={filters}
              search={search}
              searchError={searchError}
              onFilterChange={onFilterChange}
              onSearchChange={(value) => {
                setSearch(value)
                setPage(1)
              }}
            />

            <Hypotheses
              hypotheses={filteredHypotheses}
              page={page}
              onPageChange={setPage}
              emptyMessage={emptyHypothesesMessage}
            />
          </>
        )}
      </section>
    </>
  )
}

export default App;
