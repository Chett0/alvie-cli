import { useEffect, useMemo, useRef } from 'react'
import type { ReactNode } from 'react'
import type { SelectOption } from './types'

interface FilterProps {
  id: string
  label: string
  options: SelectOption[]
  selectedValues: string[]
  placeholder: string
  onChange: (values: string[]) => void
  renderBadge?: (option: SelectOption) => ReactNode
}

function Filter({
  id,
  label,
  options,
  selectedValues,
  placeholder,
  onChange,
  renderBadge,
}: FilterProps) {
  const detailsRef = useRef<HTMLDetailsElement | null>(null)
  const optionsByValue = useMemo(
    () => new Map(options.map((option) => [option.value, option])),
    [options],
  )

  useEffect(() => {
    const closeWhenClickingOutside = (event: PointerEvent) => {
      if (
        detailsRef.current?.open &&
        event.target instanceof Node &&
        !detailsRef.current.contains(event.target)
      ) {
        detailsRef.current.open = false
      }
    }

    document.addEventListener('pointerdown', closeWhenClickingOutside)

    return () => {
      document.removeEventListener('pointerdown', closeWhenClickingOutside)
    }
  }, [])

  // Return a new array so React can observe the filter state change.
  const toggleOption = (optionValue: string) => {
    const nextValues = selectedValues.includes(optionValue)
      ? selectedValues.filter((value) => value !== optionValue)
      : [...selectedValues, optionValue]

    onChange(nextValues)
  }

  return (
    <div>
      <span className="form-label fw-semibold d-block" id={`${id}-label`}>
        {label}
      </span>

      <details className="multi-select-filter" ref={detailsRef}>
        <summary
          className="form-select multi-select-summary"
          aria-labelledby={`${id}-label`}
        >
          {selectedValues.length > 0
            ? selectedValues.map((value) => {
                const option = optionsByValue.get(value) ?? {
                  value,
                  label: value,
                }

                return (
                  <span key={value}>
                    {renderBadge ? renderBadge(option) : option.label}
                  </span>
                )
              })
            : placeholder}
        </summary>

        <div className="multi-select-menu shadow-sm">
          {options.map((option) => (
            <div className="form-check" key={option.value}>
              <input
                className="form-check-input"
                type="checkbox"
                id={`${id}-${option.value}`}
                checked={selectedValues.includes(option.value)}
                onChange={() => toggleOption(option.value)}
              />
              <label
                className="form-check-label d-flex align-items-center gap-2 w-100"
                htmlFor={`${id}-${option.value}`}
              >
                {renderBadge ? renderBadge(option) : option.label}
                {renderBadge && option.label !== option.value && (
                  <span>{option.label}</span>
                )}
              </label>
            </div>
          ))}

          {selectedValues.length > 0 && (
            <button
              className="btn btn-link btn-sm p-0 mt-2"
              type="button"
              onClick={() => onChange([])}
            >
              Clear selection
            </button>
          )}
        </div>
      </details>
    </div>
  )
}

export default Filter
