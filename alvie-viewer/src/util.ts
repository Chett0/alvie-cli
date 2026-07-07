import symbolCatalog from './symbolCatalog'
import type {
  FilterValues,
  IndexedHypothesis,
  IndexedRun,
  Run,
  SelectOption,
} from './types'

export const symbolsToOptions = (
  symbols: Record<string, { name: string; color: string }>,
): SelectOption[] =>
  Object.entries(symbols).map(([key, { name: label, color }]) => ({
    value: key,
    label,
    color,
  }))

const matchesFilter = (selectedValues: string[], availableValues: string[]) =>
  selectedValues.length === 0 ||
  selectedValues.some((value) => availableValues.includes(value))

const indexRun = (
  steps: Run,
  hypothesisIndex: number,
  runIndex: number,
): IndexedRun => {
  const inputSymbols = new Set<string>()
  const outputSymbols = new Set<string>()
  const inputActors = new Set<IndexedRun['actors'][number]>()

  for (const { inputs = [], outputs = [] } of steps) {
    for (const { symbol, actor } of inputs) {
      inputSymbols.add(symbol)
      if (actor) inputActors.add(actor)
    }

    for (const symbol of outputs) outputSymbols.add(symbol)
  }

  const inputs = [...inputSymbols]
  const outputs = [...outputSymbols]
  const actors = [
    ...new Set(
      [
        ...inputActors,
        ...outputs.map((symbol) => symbolCatalog.outputs[symbol]?.actor),
      ].filter(Boolean),
    ),
  ] as IndexedRun['actors']

  const details = [
    ...inputs.map((symbol) => symbolCatalog.inputs[symbol]),
    ...outputs.map((symbol) => symbolCatalog.outputs[symbol]),
  ]

  return {
    steps,
    index: runIndex,
    actors,
    inputSymbols: inputs,
    outputSymbols: outputs,
    searchText: [
      `hypothesis ${hypothesisIndex + 1}`,
      `run ${runIndex + 1}`,
      JSON.stringify({ steps, details }),
    ].join(' ').toLowerCase(),
  }
}

export const indexHypotheses = (
  hypotheses: Run[][],
): IndexedHypothesis[] =>
  hypotheses.map((runs, index) => ({
    index,
    runs: runs.map((steps, runIndex) => indexRun(steps, index, runIndex)),
  }))

export const filterHypotheses = (
  hypotheses: IndexedHypothesis[],
  filters: FilterValues,
  searchRegex: RegExp | null,
): IndexedHypothesis[] => {
  const hasActiveFilters = Object.values(filters).some(
    (values) => values.length > 0,
  )

  if (!searchRegex && !hasActiveFilters) return hypotheses

  return hypotheses.flatMap(({ index, runs }) => {
    const matchingRuns = runs.filter(
      (run) =>
        (!searchRegex || searchRegex.test(run.searchText)) &&
        matchesFilter(filters.actors, run.actors) &&
        matchesFilter(filters.inputs, run.inputSymbols) &&
        matchesFilter(filters.outputs, run.outputSymbols),
    )

    return matchingRuns.length ? [{ index, runs: matchingRuns }] : []
  })
}
