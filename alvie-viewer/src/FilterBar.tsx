import Filter from './Filter'
import { ActorBadge, SymbolBadge } from './Badges'
import type { Actor, FilterOptions, FilterValues, SelectOption } from './types'

interface FilterBarProps {
  options: FilterOptions
  values: FilterValues
  search: string
  searchError: string
  onFilterChange: <K extends keyof FilterValues>(
    filter: K,
    values: FilterValues[K],
  ) => void
  onSearchChange: (value: string) => void
}

const renderActorBadge = ({ value }: SelectOption) => (
  <ActorBadge actor={value as Actor} />
)

const renderSymbolBadge = ({ value, color }: SelectOption) => (
  <SymbolBadge symbol={value} color={color} />
)

function FilterBar({
  options,
  values,
  search,
  searchError,
  onFilterChange,
  onSearchChange,
}: FilterBarProps) {
  return (
    <div className="row g-3 my-2 mb-4">
      <div className="col-12 col-md-6 col-xl">
        <Filter
          id="actor-filter"
          label="Actor"
          options={options.actors}
          selectedValues={values.actors}
          placeholder="All actors"
          onChange={(nextValues) => onFilterChange('actors', nextValues)}
          renderBadge={renderActorBadge}
        />
      </div>

      <div className="col-12 col-md-6 col-xl">
        <Filter
          id="input-filter"
          label="Input"
          options={options.inputs}
          selectedValues={values.inputs}
          placeholder="All inputs"
          onChange={(nextValues) => onFilterChange('inputs', nextValues)}
          renderBadge={renderSymbolBadge}
        />
      </div>

      <div className="col-12 col-md-6 col-xl">
        <Filter
          id="output-filter"
          label="Output"
          options={options.outputs}
          selectedValues={values.outputs}
          placeholder="All outputs"
          onChange={(nextValues) => onFilterChange('outputs', nextValues)}
          renderBadge={renderSymbolBadge}
        />
      </div>

      <div className="col-12 col-md-6 col-xl-4">
        <label className="form-label fw-semibold" htmlFor="search-filter">
          Search
        </label>
        <div className="search-filter-wrapper">
          <svg
            className="search-filter-icon text-secondary"
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            fill="currentColor"
            viewBox="0 0 16 16"
            aria-hidden="true"
          >
            <path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001q.044.06.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1 1 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0" />
          </svg>
          <input
            type="search"
            className={`form-control search-filter-input ${
              searchError ? 'is-invalid' : ''
            }`}
            id="search-filter"
            placeholder="Search hypotheses, runs, inputs, outputs, or details"
            value={search}
            aria-invalid={Boolean(searchError)}
            aria-describedby={searchError ? 'search-filter-error' : undefined}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
        {searchError && (
          <div
            className="invalid-feedback d-block"
            id="search-filter-error"
            role="alert"
          >
            {searchError}
          </div>
        )}
      </div>
    </div>
  )
}

export default FilterBar
