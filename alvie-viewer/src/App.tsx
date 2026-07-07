import { useDeferredValue, useMemo, useState } from 'react'
import './App.css'
import { filterHypotheses, indexHypotheses, symbolsToOptions } from './util'
import CommandRun from './CommandRun'
import SummaryStats from './SummaryStats'
import FilterBar from './FilterBar'
import Header from './Header'
import Hypotheses from './Hypotheses'
import ImportJsonModal from './ImportJsonModal'
import symbolCatalog from './symbolCatalog'
import { parseParsedOutput } from './validation'
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

function App() {
  const [parsedOutput, setParsedOutput] = useState<ParsedOutput | null>(null)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const hypotheses = parsedOutput?.hypotheses ?? EMPTY_HYPOTHESES

  // Keep typing responsive while expensive filtering catches up.
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
    filter: K,
    values: FilterValues[K],
  ) => {
    setFilters((current) => ({ ...current, [filter]: values }))
    setPage(1)
  }

  // Parse first, then validate the imported data before replacing the UI state.
  const importJson = async (file: File) => {
    const data = parseParsedOutput(JSON.parse(await file.text()))

    setParsedOutput(data)
    setSearch('')
    setFilters(EMPTY_FILTERS)
    setPage(1)
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
      <Header onImportClick={() => setIsImportModalOpen(true)} />

      {isImportModalOpen && (
        <ImportJsonModal
          onClose={() => setIsImportModalOpen(false)}
          onImport={importJson}
        />
      )}

      <section className="container-fluid my-3">
        {!parsedOutput ? (
          <div className="bg-white border rounded-3 text-center text-secondary py-5 px-3">
            Import a parsed output JSON file to view its hypotheses.
          </div>
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

export default App
