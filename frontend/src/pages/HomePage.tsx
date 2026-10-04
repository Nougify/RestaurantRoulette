import { useEffect, useMemo, useRef, useState } from 'react'

import { ApiError } from '../api/client'
import { useFilterOptions, useSpin } from '../api/restaurants'
import type { Location, Restaurant, SearchFilters } from '../api/types'
import { FilterPanel } from '../components/FilterPanel'
import { MapView } from '../components/MapView'
import { RestaurantCard } from '../components/RestaurantCard'
import { SlotCard } from '../components/SlotCard'
import { DEFAULT_CENTER } from '../config'
import { useGeolocation } from '../hooks/useGeolocation'
import { isInCoverage } from '../lib/geo'

// The reel needs to run long enough to read as a spin, even when the API answers instantly.
const MIN_SPIN_MS = 1100

const INITIAL_FILTERS: Omit<SearchFilters, 'radius'> = {
  categories: [],
  cuisines: [],
  diets: [],
  dietMatch: 'all',
  openNow: false,
}

interface SpinResult {
  restaurants: Restaurant[]
  requested: number
  // Whether some places had already been shown before this spin.
  hadHistory: boolean
}

export function HomePage() {
  const filterOptions = useFilterOptions()
  const geolocation = useGeolocation()
  const spin = useSpin()

  // A point clicked on the map, used when the device location is unusable.
  const [pickedOrigin, setPickedOrigin] = useState<Location | null>(null)
  // null until the visitor changes the radius; until then the API's default applies.
  const [filters, setFilters] = useState<Omit<SearchFilters, 'radius'> & { radius?: number }>(
    INITIAL_FILTERS,
  )
  const [count, setCount] = useState(3)
  const [result, setResult] = useState<SpinResult | null>(null)
  const [isShuffling, setIsShuffling] = useState(false)
  const [highlightedId, setHighlightedId] = useState<number | null>(null)
  const [pickedId, setPickedId] = useState<number | null>(null)
  // Ids shown so far, tagged with the search they belong to (see `seen` below).
  const [history, setHistory] = useState<{ searchKey: string; ids: number[] }>({
    searchKey: '',
    ids: [],
  })

  // --- Where to search from -------------------------------------------------------------
  const deviceLocation = geolocation.status === 'located' ? geolocation.location : null
  const deviceOutsideCoverage = deviceLocation !== null && !isInCoverage(deviceLocation)
  const canPickOnMap = geolocation.status === 'unavailable' || deviceOutsideCoverage
  const origin = pickedOrigin ?? (deviceOutsideCoverage ? null : deviceLocation)

  // --- What to search for ---------------------------------------------------------------
  const radius = filters.radius ?? filterOptions.data?.radius.default ?? 2000
  const searchFilters: SearchFilters = { ...filters, radius }

  // "Previously shown" only lasts until the search changes. Rather than clearing the
  // history in an effect whenever inputs change, the history remembers which search it
  // was recorded for and is simply ignored when that no longer matches.
  const searchKey = JSON.stringify({ origin, searchFilters })
  const seen = history.searchKey === searchKey ? history.ids : []

  // Names for the slot-machine reel: places already seen, padded with cuisine names.
  const reel = useMemo(() => {
    const names = (result?.restaurants ?? []).map((r) => r.name)
    const cuisines = (filterOptions.data?.cuisines ?? []).map((c) => c.name.replaceAll('_', ' '))
    return [...names, ...cuisines].sort(() => Math.random() - 0.5)
  }, [result, filterOptions.data])

  async function handleSpin() {
    if (origin === null) return
    setIsShuffling(true)
    setPickedId(null)
    setHighlightedId(null)
    try {
      // Wait for both the API and the minimum reel time, whichever is longer.
      const [restaurants] = await Promise.all([
        spin.mutateAsync({ location: origin, filters: searchFilters, count, seen }),
        new Promise((resolve) => setTimeout(resolve, MIN_SPIN_MS)),
      ])
      setResult({ restaurants, requested: count, hadHistory: seen.length > 0 })
      setHistory({ searchKey, ids: [...new Set([...seen, ...restaurants.map((r) => r.id)])] })
    } catch {
      // The error is shown from `spin.error` below.
    } finally {
      setIsShuffling(false)
    }
  }

  // Results appear below the filters; scroll them into view when a spin starts and ends.
  const resultsRef = useRef<HTMLElement>(null)
  useEffect(() => {
    resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [isShuffling, result])

  const shown = useMemo(() => result?.restaurants ?? [], [result])
  const visible = useMemo(
    () => (pickedId === null ? shown : shown.filter((r) => r.id === pickedId)),
    [shown, pickedId],
  )
  // Numbers come from the full spin, so the picked place keeps its number when alone.
  // useMemo returns the same array until its inputs change; the map refits only when the
  // array changes, so highlighting a card does not jump the map around.
  const pins = useMemo(
    () => visible.map((restaurant) => ({ restaurant, number: shown.indexOf(restaurant) + 1 })),
    [visible, shown],
  )

  return (
    <div className="flex h-full flex-col lg:grid lg:grid-cols-[420px_1fr]">
      <aside className="order-2 flex min-h-0 flex-col border-zinc-200 bg-white lg:order-1 lg:border-r">
        <div className="flex-1 space-y-6 overflow-y-auto p-5">
          <LocationNotice
            geolocation={geolocation}
            outsideCoverage={deviceOutsideCoverage}
            pickedOrigin={pickedOrigin}
            onUseDefault={() => setPickedOrigin(DEFAULT_CENTER)}
          />

          {filterOptions.isPending && <p className="text-sm text-zinc-500">Loading filters…</p>}
          {filterOptions.isError && (
            <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
              {filterOptions.error.message}
            </p>
          )}
          {filterOptions.data && (
            <FilterPanel
              options={filterOptions.data}
              filters={searchFilters}
              onFiltersChange={setFilters}
              count={count}
              onCountChange={setCount}
            />
          )}

          <section ref={resultsRef} className="scroll-mt-5 space-y-3" aria-live="polite">
            {isShuffling &&
              Array.from({ length: count }, (_, index) => (
                <SlotCard key={index} number={index + 1} reel={reel} />
              ))}

            {!isShuffling && spin.isError && (
              <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
                {spin.error instanceof ApiError ? spin.error.message : 'The spin failed.'}
              </p>
            )}

            {!isShuffling && result && (
              <>
                <ResultNotice result={result} />
                {pickedId !== null && (
                  <button
                    type="button"
                    onClick={() => setPickedId(null)}
                    className="text-sm font-medium text-accent hover:text-accent-hover"
                  >
                    ← Back to all choices
                  </button>
                )}
                {visible.map((restaurant) => (
                  <RestaurantCard
                    key={restaurant.id}
                    restaurant={restaurant}
                    number={shown.indexOf(restaurant) + 1}
                    origin={origin}
                    highlighted={restaurant.id === highlightedId}
                    onSelect={() => setHighlightedId(restaurant.id)}
                    onPick={pickedId === null ? () => setPickedId(restaurant.id) : undefined}
                  />
                ))}
              </>
            )}
          </section>
        </div>

        <div className="border-t border-zinc-200 p-4">
          <button
            type="button"
            onClick={handleSpin}
            disabled={origin === null || isShuffling || !filterOptions.data}
            className="w-full rounded-xl bg-accent py-3 text-base font-semibold text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            {isShuffling ? 'Spinning…' : result ? 'Spin again' : 'Spin'}
          </button>
        </div>
      </aside>

      <div className="order-1 h-72 shrink-0 lg:order-2 lg:h-full">
        <MapView
          origin={origin}
          radius={radius}
          pins={pins}
          highlightedId={highlightedId}
          onSelectRestaurant={setHighlightedId}
          onPickOrigin={canPickOnMap ? setPickedOrigin : undefined}
        />
      </div>
    </div>
  )
}

function LocationNotice({
  geolocation,
  outsideCoverage,
  pickedOrigin,
  onUseDefault,
}: {
  geolocation: ReturnType<typeof useGeolocation>
  outsideCoverage: boolean
  pickedOrigin: Location | null
  onUseDefault: () => void
}) {
  if (geolocation.status === 'locating') {
    return <p className="text-sm text-zinc-500">Finding your location…</p>
  }
  if (geolocation.status === 'located' && !outsideCoverage) return null

  const reason =
    geolocation.status === 'unavailable'
      ? geolocation.reason
      : 'You seem to be outside Metro Vancouver, which is the only area covered.'

  return (
    <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-sm text-zinc-700">
      <p>
        {reason}{' '}
        {pickedOrigin
          ? 'Click the map to move your search point.'
          : 'Click the map to choose where to search from.'}
      </p>
      {!pickedOrigin && (
        <button
          type="button"
          onClick={onUseDefault}
          className="mt-2 font-medium text-accent hover:text-accent-hover"
        >
          Use downtown Vancouver
        </button>
      )}
    </div>
  )
}

function ResultNotice({ result }: { result: SpinResult }) {
  const found = result.restaurants.length
  if (found === 0) {
    return (
      <p className="rounded-lg bg-zinc-100 p-3 text-sm text-zinc-700">
        {result.hadHistory
          ? "You've seen every place that matches these filters. Change the filters to start fresh."
          : 'No places match these filters. Try a bigger radius or fewer filters.'}
      </p>
    )
  }
  if (found < result.requested) {
    return (
      <p className="rounded-lg bg-zinc-100 p-3 text-sm text-zinc-700">
        {result.hadHistory
          ? `Only ${found} new ${found === 1 ? 'choice' : 'choices'}: you've seen most places that match these filters.`
          : `Only ${found} ${found === 1 ? 'place matches' : 'places match'} these filters.`}
      </p>
    )
  }
  return null
}
