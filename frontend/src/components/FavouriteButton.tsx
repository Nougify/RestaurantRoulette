import { useLocation, useNavigate } from 'react-router'

import { useFavourites, useToggleFavourite } from '../api/favourites'
import { useAuth } from '../auth/AuthContext'

/** A heart that saves or unsaves a restaurant. Signed-out visitors are sent to log in. */
export function FavouriteButton({ restaurantId }: { restaurantId: number }) {
  const { token } = useAuth()
  const favourites = useFavourites()
  const toggleFavourite = useToggleFavourite()
  const navigate = useNavigate()
  const location = useLocation()

  const saved = favourites.data?.some((restaurant) => restaurant.id === restaurantId) ?? false

  function handleClick() {
    if (token === null) {
      // Remember where they were so the login page can bring them back.
      navigate('/login', { state: { from: location.pathname } })
      return
    }
    toggleFavourite.mutate({ restaurantId, save: !saved })
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={toggleFavourite.isPending}
      aria-pressed={saved}
      aria-label={saved ? 'Remove from favourites' : 'Save to favourites'}
      title={saved ? 'Remove from favourites' : 'Save to favourites'}
      className="rounded-full p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-accent disabled:opacity-50"
    >
      <svg
        viewBox="0 0 24 24"
        className={`h-5 w-5 ${saved ? 'fill-accent text-accent' : 'fill-none'}`}
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M12 21s-7.5-4.6-9.5-9.2C1 8.1 3.3 4.5 7 4.5c2.1 0 3.6 1.1 5 2.9 1.4-1.8 2.9-2.9 5-2.9 3.7 0 6 3.6 4.5 7.3C19.5 16.4 12 21 12 21z"
        />
      </svg>
    </button>
  )
}
