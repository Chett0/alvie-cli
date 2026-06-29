import { useEffect, useRef } from 'react'

function Filter({
  id,
  label,
  options,
  selectedValues,
  placeholder,
  onChange,
  renderBadge,
}) {
  const detailsRef = useRef(null)
  const optionsByValue = new Map(
    options.map((option) => [option.value, option]),
  )

  // Close filter select when clicking outside of it
  useEffect(() => {
    const closeWhenClickingOutside = (event) => {
      if (
        detailsRef.current?.open &&
        !detailsRef.current.contains(event.target)
      ) {
        detailsRef.current.open = false
      }
    }

    document.addEventListener('pointerdown', closeWhenClickingOutside)

    // Cleanup function to remove the event listener when the component unmounts
    return () => {
      document.removeEventListener('pointerdown', closeWhenClickingOutside)
    }
  }, [])

  // Selected values: create a new array to update the prop, otherwise React will not re-render properly.
  // Remove them if already selected
  const toggleOption = (optionValue) => {
    const nextValues = selectedValues.includes(optionValue)
      ? selectedValues.filter((value) => value !== optionValue)
      : [...selectedValues, optionValue];

    onChange(nextValues);
  };

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
  );
}

export default Filter;
