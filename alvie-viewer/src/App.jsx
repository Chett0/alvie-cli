// React
// useMemo: memoize expensive calculations for faster searching
import { useDeferredValue, useMemo, useState } from 'react'

// Styles
import './App.css'

// Data
import symbolCatalog from './output_symbols.json'
import { filterHypotheses, indexHypotheses, symbolsToOptions } from './util'

// Components
import CommandRun from './CommandRun'
import SummaryStats from "./SummaryStats";
import FilterBar from "./FilterBar";
import Header from './Header'
import Hypotheses from './Hypotheses'
import ImportJsonModal from './ImportJsonModal'

// Starting empty states for hypotheses and filters
const EMPTY_HYPOTHESES = []
const EMPTY_FILTERS = {
  actors: [],
  inputs: [],
  outputs: [],
}

// Available filters
const FILTER_OPTIONS = {
  actors: [
    { value: 'Attacker', label: 'Attacker' },
    { value: 'Enclave', label: 'Enclave' },
    { value: 'No actor', label: 'No actor' },
  ],
  inputs: symbolsToOptions(symbolCatalog.inputs),
  outputs: symbolsToOptions(symbolCatalog.outputs),
}

function App() {

  const [parsedOutput, setParsedOutput] = useState(null)
  const [isImportModalOpen, setIsImportModalOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [page, setPage] = useState(1)
  const hypotheses = parsedOutput?.hypotheses ?? EMPTY_HYPOTHESES

  // Show old search value while data is loading. avoid lagging
  const deferredSearch = useDeferredValue(search.trim())

  // Regex validation and error message
  // useMemo to avoid re-parsing the regex on every render
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
        searchError: `Invalid regular expression. ${reason || ''}`
      }
    }
  }, [deferredSearch])

  // Update filters and reset page to 1 when a filter changes
  const onFilterChange = (filter, values) => {
    setFilters((current) => ({ ...current, [filter]: values }))
    setPage(1)
  }

  // Parse and validate imported data before replacing the current application state.
  const importJson = async (file) => {
    const data = JSON.parse(await file.text())

    if (!data || !Array.isArray(data.hypotheses) || !data.recap) {
      throw new Error('The file does not contain hypotheses and recap data.')
    }

    setParsedOutput(data)
    setSearch('')
    setFilters(EMPTY_FILTERS)
    setPage(1)
  }

  // Cache data between re-renders for better performance, avoiding recomputation
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

  // Explain empty results unless the search field already displays a regex error.
  const emptyHypothesesMessage = searchError
    ? ''
    : indexedHypotheses.length === 0
      ? 'The imported file contains no hypotheses.'
      : 'No hypotheses match the current search and filters.'

  return (
    <>
      {/* Title and import button */}
      <Header onImportClick={() => setIsImportModalOpen(true)} />
      {isImportModalOpen && (
        <ImportJsonModal
          onClose={() => setIsImportModalOpen(false)}
          onImport={importJson}
        />
      )}

      <section className="container-fluid my-3">
        {!parsedOutput ? (
          // Initial placeholder
          <div className="bg-white border rounded-3 text-center text-secondary py-5 px-3">
            Import a parsed output JSON file to view its hypotheses.
          </div>
        ) : (
          <>

            {/* Recap */}

            <CommandRun
              key={parsedOutput.start}
              executable={parsedOutput.executable}
              args={parsedOutput.args}
              start={parsedOutput.start}
              end={parsedOutput.end}
            />

            <SummaryStats
              recap={parsedOutput.recap}
            />

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
