import { Link, Navigate } from 'react-router'

import { useFavourites } from '../api/favourites'
import { useAuth } from '../auth/AuthContext'
import { RestaurantCard } from '../components/RestaurantCard'

export function FavouritesPage() {
  const { token } = useAuth()
  const favourites = useFavourites()

  // A protected page: signed-out visitors are redirected, and brought back after logging in.
  if (token === null) return <Navigate to="/login" replace state={{ from: '/favourites' }} />

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-2xl space-y-4 p-6">
        <h1 className="text-xl font-semibold">Your favourites</h1>

        {favourites.isPending && <p className="text-sm text-zinc-500">Loading…</p>}
        {favourites.isError && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
            {favourites.error.message}
          </p>
        )}
        {favourites.data?.length === 0 && (
          <p className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">
            Nothing saved yet. Tap the heart on a place to keep it here.{' '}
            <Link to="/" className="font-medium text-accent hover:text-accent-hover">
              Spin for somewhere to eat
            </Link>
          </p>
        )}
        {favourites.data?.map((restaurant) => (
          <RestaurantCard key={restaurant.id} restaurant={restaurant} />
        ))}
      </div>
    </div>
  )
}
