import { useState } from 'react'
import type { ReactNode } from 'react'

import type { Category, Diet, FilterOptions, SearchFilters } from '../api/types'
import { formatDistance, label } from '../lib/format'
import { Chip } from './Chip'

const CUISINES_SHOWN_COLLAPSED = 12
const MIN_RADIUS_M = 500
const RADIUS_STEP_M = 250

interface FilterPanelProps {
  options: FilterOptions
  filters: SearchFilters
  onFiltersChange: (filters: SearchFilters) => void
  count: number
  onCountChange: (count: number) => void
}

/** Add `value` to the list if it is missing, or remove it if present. */
function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value]
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-2">
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {title}
      </legend>
      {children}
    </fieldset>
  )
}

/**
 * The search controls. It owns no filter state itself: it shows the values it is given
 * and reports changes upward ("controlled component"), so the page decides what to do.
 */
export function FilterPanel({
  options,
  filters,
  onFiltersChange,
  count,
  onCountChange,
}: FilterPanelProps) {
  const [showAllCuisines, setShowAllCuisines] = useState(false)
  const update = (changes: Partial<SearchFilters>) => onFiltersChange({ ...filters, ...changes })

  const cuisines = showAllCuisines
    ? options.cuisines
    : options.cuisines.slice(0, CUISINES_SHOWN_COLLAPSED)

  return (
    <div className="space-y-6">
      <Section title={`Within ${formatDistance(filters.radius)}`}>
        <input
          type="range"
          min={MIN_RADIUS_M}
          max={options.radius.max}
          step={RADIUS_STEP_M}
          value={filters.radius}
          onChange={(event) => update({ radius: Number(event.target.value) })}
          className="w-full accent-accent"
          aria-label="Search radius"
        />
      </Section>

      <Section title="Choices per spin">
        <div className="flex gap-2">
          {Array.from({ length: options.max_spin_count }, (_, index) => index + 1).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => onCountChange(n)}
              aria-pressed={count === n}
              className={`h-9 w-9 rounded-lg border text-sm font-medium ${
                count === n
                  ? 'border-accent bg-accent text-white'
                  : 'border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </Section>

      <Section title="Type">
        <div className="flex flex-wrap gap-2">
          {options.categories.map((category: Category) => (
            <Chip
              key={category}
              label={label(category)}
              selected={filters.categories.includes(category)}
              onToggle={() => update({ categories: toggle(filters.categories, category) })}
            />
          ))}
        </div>
      </Section>

      <Section title="Dietary needs">
        <div className="flex flex-wrap gap-2">
          {options.diets.map((diet: Diet) => (
            <Chip
              key={diet}
              label={label(diet)}
              selected={filters.diets.includes(diet)}
              onToggle={() => update({ diets: toggle(filters.diets, diet) })}
            />
          ))}
        </div>
        {filters.diets.length > 1 && (
          <div className="flex items-center gap-3 pt-1 text-sm text-zinc-600">
            <span>Must cater for</span>
            {(['all', 'any'] as const).map((mode) => (
              <label key={mode} className="flex items-center gap-1">
                <input
                  type="radio"
                  name="diet-match"
                  checked={filters.dietMatch === mode}
                  onChange={() => update({ dietMatch: mode })}
                  className="accent-accent"
                />
                {mode === 'all' ? 'all of them' : 'any of them'}
              </label>
            ))}
          </div>
        )}
      </Section>

      <Section title="Cuisine">
        <div className="flex flex-wrap gap-2">
          {cuisines.map(({ name }) => (
            <Chip
              key={name}
              label={label(name)}
              selected={filters.cuisines.includes(name)}
              onToggle={() => update({ cuisines: toggle(filters.cuisines, name) })}
            />
          ))}
        </div>
        {options.cuisines.length > CUISINES_SHOWN_COLLAPSED && (
          <button
            type="button"
            onClick={() => setShowAllCuisines(!showAllCuisines)}
            className="text-sm font-medium text-accent hover:text-accent-hover"
          >
            {showAllCuisines ? 'Show fewer' : `Show all ${options.cuisines.length}`}
          </button>
        )}
      </Section>

      <label className="flex items-center gap-2 text-sm font-medium text-zinc-700">
        <input
          type="checkbox"
          checked={filters.openNow}
          onChange={(event) => update({ openNow: event.target.checked })}
          className="h-4 w-4 accent-accent"
        />
        Open now
      </label>
    </div>
  )
}
