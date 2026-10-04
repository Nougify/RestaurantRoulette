import { useEffect, useRef } from 'react'

import type { Location, Restaurant } from '../api/types'
import { formatDistance, label } from '../lib/format'
import { FavouriteButton } from './FavouriteButton'

interface RestaurantCardProps {
  restaurant: Restaurant
  // The number shown on the card and on its map pin.
  number?: number
  // Where directions start from; Google Maps uses the device's location if omitted.
  origin?: Location | null
  highlighted?: boolean
  onSelect?: () => void
  onPick?: () => void
}

function OpenBadge({ open }: { open: boolean | null }) {
  if (open === null) return <span className="text-zinc-400">Hours unknown</span>
  return open ? (
    <span className="font-medium text-emerald-700">Open now</span>
  ) : (
    <span className="text-zinc-500">Closed now</span>
  )
}

function directionsUrl(restaurant: Restaurant, origin?: Location | null): string {
  const url = new URL('https://www.google.com/maps/dir/')
  url.searchParams.set('api', '1')
  url.searchParams.set('destination', `${restaurant.lat},${restaurant.lon}`)
  if (origin) url.searchParams.set('origin', `${origin.lat},${origin.lon}`)
  return url.toString()
}

const actionClass =
  'rounded-md border border-zinc-300 px-2.5 py-1 text-sm text-zinc-700 hover:border-zinc-400 hover:bg-zinc-50'

export function RestaurantCard({
  restaurant,
  number,
  origin,
  highlighted = false,
  onSelect,
  onPick,
}: RestaurantCardProps) {
  const ref = useRef<HTMLElement>(null)

  // When the matching map pin is clicked, bring this card into view.
  useEffect(() => {
    if (highlighted) ref.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [highlighted])

  const details = [label(restaurant.category), ...restaurant.cuisines.slice(0, 3).map(label)]

  return (
    <article
      ref={ref}
      onClick={onSelect}
      className={`rounded-xl border bg-white p-4 transition-shadow ${
        highlighted ? 'border-accent shadow-md' : 'border-zinc-200'
      } ${onSelect ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start gap-3">
        {number !== undefined && (
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-sm font-semibold text-white">
            {number}
          </span>
        )}
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-base font-semibold leading-tight">{restaurant.name}</h3>
            <FavouriteButton restaurantId={restaurant.id} />
          </div>
          <p className="mt-0.5 text-sm text-zinc-500">{details.join(' · ')}</p>
          <p className="mt-1 flex flex-wrap gap-x-3 text-sm">
            {restaurant.distance_m !== undefined && (
              <span className="text-zinc-700">{formatDistance(restaurant.distance_m)} away</span>
            )}
            <OpenBadge open={restaurant.open_now} />
          </p>
          {restaurant.address && (
            <p className="mt-1 text-sm text-zinc-500">{restaurant.address}</p>
          )}
          {restaurant.diets.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-1.5">
              {restaurant.diets.map((diet) => (
                <li
                  key={diet}
                  className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-hover"
                >
                  {label(diet)}
                </li>
              ))}
            </ul>
          )}

          {/* stopPropagation: a click on a link or button should not also select the card. */}
          <div className="mt-3 flex flex-wrap gap-2" onClick={(event) => event.stopPropagation()}>
            <a
              href={directionsUrl(restaurant, origin)}
              target="_blank"
              rel="noreferrer"
              className={actionClass}
            >
              Directions
            </a>
            {restaurant.website && (
              <a href={restaurant.website} target="_blank" rel="noreferrer" className={actionClass}>
                Website
              </a>
            )}
            {restaurant.phone && (
              <a href={`tel:${restaurant.phone}`} className={actionClass}>
                Call
              </a>
            )}
            {onPick && (
              <button
                type="button"
                onClick={onPick}
                className="rounded-md bg-accent px-2.5 py-1 text-sm font-medium text-white hover:bg-accent-hover"
              >
                Pick this one
              </button>
            )}
          </div>
        </div>
      </div>
    </article>
  )
}
