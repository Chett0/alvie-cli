import symbolCatalog from './output_symbols.json'

/**
 * Map a JSON symbol catalog to the complete option objects used by filters.
 *
 * { key: { name, color } } -> [{ value: key, label: name, color }]
 */
export const symbolsToOptions = (symbols) =>
  Object.entries(symbols).map(([key, { name: label, color }]) => ({
    value: key,
    label,
    color,
  }))

const matchesFilter = (selectedValues, availableValues) =>
  selectedValues.length === 0 ||
  selectedValues.some((value) => availableValues.includes(value))

const indexRun = (steps, hypothesisIndex, runIndex) => {
  const inputSymbols = new Set()
  const outputSymbols = new Set()
  const inputActors = new Set()

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
    ...new Set([
      ...inputActors,
      ...outputs.map((symbol) => symbolCatalog.outputs[symbol]?.actor),
    ].filter(Boolean)),
  ]
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

const matchesRun = (run, filters, searchRegex) =>
  (!searchRegex || searchRegex.test(run.searchText)) &&
  matchesFilter(filters.actors, run.actors) &&
  matchesFilter(filters.inputs, run.inputSymbols) &&
  matchesFilter(filters.outputs, run.outputSymbols)

export const indexHypotheses = (hypotheses) =>
  hypotheses.map((runs, index) => ({
    index,
    runs: runs.map((steps, runIndex) => indexRun(steps, index, runIndex)),
  }))

export const filterHypotheses = (hypotheses, filters, searchRegex) => {
  const hasActiveFilters = Object.values(filters).some(
    (values) => values.length > 0,
  )

  if (!searchRegex && !hasActiveFilters) return hypotheses

  return hypotheses.flatMap(({ index, runs }) => {
    const matchingRuns = runs.filter((run) => matchesRun(run, filters, searchRegex))

    return matchingRuns.length ? [{ index, runs: matchingRuns }] : []
  })
}
