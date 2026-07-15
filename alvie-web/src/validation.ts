import type { Actor, CommandArgument, ParsedOutput, RunStep, ValidationErrorContext } from './types'

const ACTORS: Actor[] = ['Attacker', 'Enclave', 'No actor']

const failValidation = ({ path, expected }: ValidationErrorContext): never => {
  throw new Error(`Invalid parsed output JSON: ${path} must be ${expected}.`)
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const readString = (value: unknown, path: string): string => {
  if (typeof value !== 'string') failValidation({ path, expected: 'a string' })
  return value as string
}

const readNumber = (value: unknown, path: string): number => {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    failValidation({ path, expected: 'a finite number' })
  }

  return value as number
}

const readCommandArgument = (value: unknown, path: string): CommandArgument => {
  if (!isRecord(value)) failValidation({ path, expected: 'an object' })
  const record = value as Record<string, unknown>

  return {
    flag: readString(record.flag, `${path}.flag`),
    ...(record.value === undefined
      ? {}
      : { value: readString(record.value, `${path}.value`) }),
  }
}

const readActor = (value: unknown, path: string): Actor => {
  if (typeof value !== 'string' || !ACTORS.includes(value as Actor)) {
    failValidation({ path, expected: '"Attacker", "Enclave", or "No actor"' })
  }

  return value as Actor
}

const formatStepLocation = (
  hypothesisIndex: number,
  runIndex: number,
  stepIndex: number,
  detail?: string,
) =>
  [
    `hypothesis ${hypothesisIndex + 1}`,
    `run ${runIndex + 1}`,
    `step ${stepIndex + 1}`,
    detail,
  ]
    .filter(Boolean)
    .join(', ')

const readStep = (
  value: unknown,
  hypothesisIndex: number,
  runIndex: number,
  stepIndex: number,
): RunStep => {
  const stepPath = formatStepLocation(hypothesisIndex, runIndex, stepIndex)

  if (!isRecord(value)) failValidation({ path: stepPath, expected: 'an object' })
  const record = value as Record<string, unknown>

  if (!Array.isArray(record.inputs)) {
    failValidation({
      path: formatStepLocation(hypothesisIndex, runIndex, stepIndex, 'inputs'),
      expected: 'an array',
    })
  }
  if (!Array.isArray(record.outputs)) {
    failValidation({
      path: formatStepLocation(hypothesisIndex, runIndex, stepIndex, 'outputs'),
      expected: 'an array',
    })
  }

  const inputs = record.inputs as unknown[]
  const outputs = record.outputs as unknown[]

  return {
    inputs: inputs.map((input: unknown, inputIndex: number) => {
      const inputPath = formatStepLocation(
        hypothesisIndex,
        runIndex,
        stepIndex,
        `input ${inputIndex + 1}`,
      )

      if (!isRecord(input)) failValidation({ path: inputPath, expected: 'an object' })
      const inputRecord = input as Record<string, unknown>

      return {
        symbol: readString(inputRecord.symbol, `${inputPath}, symbol`),
        actor: readActor(inputRecord.actor, `${inputPath}, actor`),
      }
    }),
    outputs: outputs.map((output: unknown, outputIndex: number) =>
      readString(
        output,
        formatStepLocation(
          hypothesisIndex,
          runIndex,
          stepIndex,
          `output ${outputIndex + 1}`,
        ),
      ),
    ),
  }
}

export const validateParsedOutput = (value: unknown): ParsedOutput => {
  if (!isRecord(value)) failValidation({ path: 'root', expected: 'an object' })
  const record = value as Record<string, unknown>

  if (!Array.isArray(record.args)) failValidation({ path: 'args', expected: 'an array' })
  if (!isRecord(record.recap)) failValidation({ path: 'recap', expected: 'an object' })
  if (!Array.isArray(record.hypotheses)) {
    failValidation({ path: 'hypotheses', expected: 'an array' })
  }

  const args = record.args as unknown[]
  const recapRecord = record.recap as Record<string, unknown>
  const hypotheses = record.hypotheses as unknown[]

  // Validating recap
  const recap: Record<string, number> = {}
  for (const [key, value] of Object.entries(recapRecord)) {
    recap[key] = readNumber(value, `recap.${key}`) // ensure recap values are numbers
  }

  // summary fields
  readNumber(recap.hypotheses, 'recap.hypotheses')
  readNumber(recap.runs, 'recap.runs')
  readNumber(recap.steps, 'recap.steps')

  return {
    executable: readString(record.executable, 'executable'),
    args: args.map((argument: unknown, index: number) =>
      readCommandArgument(argument, `args[${index}]`),
    ),
    start: readString(record.start, 'start'),
    end: readString(record.end, 'end'),
    recap: recap as ParsedOutput['recap'],
    hypotheses: hypotheses.map((hypothesis: unknown, hypothesisIndex: number) => {
      if (!Array.isArray(hypothesis)) {
        failValidation({
          path: `hypothesis ${hypothesisIndex + 1}`,
          expected: 'an array of runs',
        })
      }

      const runs = hypothesis as unknown[]

      return runs.map((run: unknown, runIndex: number) => {
        if (!Array.isArray(run)) {
          failValidation({
            path: `hypothesis ${hypothesisIndex + 1}, run ${runIndex + 1}`,
            expected: 'an array of steps',
          })
        }

        const steps = run as unknown[]

        return steps.map((step: unknown, stepIndex: number) =>
          readStep(step, hypothesisIndex, runIndex, stepIndex),
        )
      })
    }),
  }
}
