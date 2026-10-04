import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '../auth/AuthContext'
import { apiFetch } from './client'
import type { Restaurant } from './types'

/** The signed-in user's favourites. Does nothing while signed out. */
export function useFavourites() {
  const { token } = useAuth()
  return useQuery({
    queryKey: ['favourites', token],
    queryFn: async () => {
      const data = await apiFetch<{ restaurants: Restaurant[] }>('/api/favourites', { token })
      return data.restaurants
    },
    enabled: token !== null,
  })
}

/** Save or unsave a restaurant, then refresh the favourites list. */
export function useToggleFavourite() {
  const { token } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ restaurantId, save }: { restaurantId: number; save: boolean }) =>
      apiFetch<void>(`/api/favourites/${restaurantId}`, {
        method: save ? 'PUT' : 'DELETE',
        token,
      }),
    // Marking the cached list stale makes every component showing it refetch.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['favourites'] }),
  })
}
