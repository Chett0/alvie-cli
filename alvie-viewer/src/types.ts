export type Actor = 'Attacker' | 'Enclave' | 'No actor'

export interface CommandArgument {
  flag: string
  value?: string
}

export interface Recap {
  hypotheses: number
  runs: number
  steps: number
  [symbol: string]: number
}

export interface StepInput {
  symbol: string
  actor: Actor
}

export interface RunStep {
  inputs: StepInput[]
  outputs: string[]
}

export type Run = RunStep[]
export type Hypothesis = Run[]

export interface ParsedOutput {
  executable: string
  args: CommandArgument[]
  start: string
  end: string
  recap: Recap
  hypotheses: Hypothesis[]
}

export interface InputSymbolDetails {
  name: string
  description: string
  color: string
}

export interface OutputSymbolDetails extends InputSymbolDetails {
  actor: Actor
}

export interface SymbolCatalog {
  inputs: Record<string, InputSymbolDetails>
  outputs: Record<string, OutputSymbolDetails>
}

export interface SelectOption {
  value: string
  label: string
  color?: string
}

export interface FilterValues {
  actors: string[]
  inputs: string[]
  outputs: string[]
}

export interface FilterOptions {
  actors: SelectOption[]
  inputs: SelectOption[]
  outputs: SelectOption[]
}

export interface IndexedRun {
  steps: Run
  index: number
  actors: Actor[]
  inputSymbols: string[]
  outputSymbols: string[]
  searchText: string
}

export interface IndexedHypothesis {
  index: number
  runs: IndexedRun[]
}

export interface ValidationErrorContext {
  path: string
  expected: string
}
