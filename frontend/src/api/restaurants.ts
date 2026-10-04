import { useMutation, useQuery } from '@tanstack/react-query'

import { apiFetch } from './client'
import type { FilterOptions, Location, Restaurant, SearchFilters } from './types'

/** Turn the filter state into the API's query parameters (lists are comma-separated). */
function searchParams(location: Location, filters: SearchFilters) {
  return {
    lat: location.lat,
    lon: location.lon,
    radius: filters.radius,
    category: filters.categories.join(','),
    cuisine: filters.cuisines.join(','),
    diet: filters.diets.join(','),
    diet_match: filters.dietMatch,
    open_now: filters.openNow,
  }
}

export interface SpinRequest {
  location: Location
  filters: SearchFilters
  count: number
  seen: number[]
}

export async function spinRestaurants(request: SpinRequest): Promise<Restaurant[]> {
  const data = await apiFetch<{ restaurants: Restaurant[] }>('/api/restaurants/spin', {
    params: {
      ...searchParams(request.location, request.filters),
      count: request.count,
      seen: request.seen.join(','),
    },
  })
  return data.restaurants
}

/** The choices for the filter controls. They only change on re-import, so cache them forever. */
export function useFilterOptions() {
  return useQuery({
    queryKey: ['filters'],
    queryFn: () => apiFetch<FilterOptions>('/api/filters'),
    staleTime: Infinity,
  })
}

/**
 * A spin is a mutation rather than a query: it runs when the visitor presses the button,
 * and every call should give a new random answer, so caching it would be wrong.
 */
export function useSpin() {
  return useMutation({ mutationFn: spinRestaurants })
}
