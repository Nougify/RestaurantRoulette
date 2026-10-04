import L from 'leaflet'
import { useEffect, useMemo } from 'react'
import { Circle, CircleMarker, MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'

import type { Location, Restaurant } from '../api/types'
import { DEFAULT_CENTER } from '../config'

interface MapViewProps {
  // The search point; null until it is known.
  origin: Location | null
  radius: number
  // Each restaurant with the number shown on its card, so pin and card always match.
  pins: { restaurant: Restaurant; number: number }[]
  highlightedId: number | null
  onSelectRestaurant: (id: number) => void
  // Only given when the visitor needs to choose a point by clicking the map.
  onPickOrigin?: (location: Location) => void
}

/**
 * A numbered map pin. Leaflet's default pin is an image; a divIcon is plain HTML, so it
 * can show the same number as the matching card and be styled with Tailwind classes.
 */
function numberedIcon(number: number, highlighted: boolean) {
  return L.divIcon({
    className: '',
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<span class="flex h-[30px] w-[30px] items-center justify-center rounded-full border-2 border-white text-sm font-semibold text-white shadow-md ${
      highlighted ? 'bg-accent scale-125' : 'bg-zinc-900'
    }">${number}</span>`,
  })
}

/**
 * Moves the map when the data changes. MapContainer only reads its `center` once, so
 * later changes are applied through the Leaflet map object that `useMap` returns.
 */
function FitToContent({ origin, restaurants }: { origin: Location | null; restaurants: Restaurant[] }) {
  const map = useMap()

  useEffect(() => {
    if (restaurants.length > 0) {
      const points = restaurants.map((r) => [r.lat, r.lon] as [number, number])
      if (origin) points.push([origin.lat, origin.lon])
      map.fitBounds(points, { padding: [50, 50], maxZoom: 17 })
    } else if (origin) {
      map.setView([origin.lat, origin.lon], 14)
    }
  }, [map, origin, restaurants])

  return null
}

function ClickToPick({ onPick }: { onPick: (location: Location) => void }) {
  useMapEvents({
    click: (event) => onPick({ lat: event.latlng.lat, lon: event.latlng.lng }),
  })
  return null
}

export function MapView({
  origin,
  radius,
  pins,
  highlightedId,
  onSelectRestaurant,
  onPickOrigin,
}: MapViewProps) {
  const start = origin ?? DEFAULT_CENTER
  const restaurants = useMemo(() => pins.map((pin) => pin.restaurant), [pins])

  return (
    <MapContainer
      center={[start.lat, start.lon]}
      zoom={13}
      className={`h-full w-full ${onPickOrigin ? 'cursor-crosshair' : ''}`}
    >
      {/* OpenStreetMap's tiles are free to use with this attribution, and need no API key. */}
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {origin && (
        <>
          <Circle
            center={[origin.lat, origin.lon]}
            radius={radius}
            pathOptions={{ color: '#e8590c', weight: 1, fillOpacity: 0.05 }}
          />
          <CircleMarker
            center={[origin.lat, origin.lon]}
            radius={8}
            pathOptions={{ color: '#ffffff', weight: 3, fillColor: '#2563eb', fillOpacity: 1 }}
          />
        </>
      )}
      {pins.map(({ restaurant, number }) => (
        <Marker
          key={restaurant.id}
          position={[restaurant.lat, restaurant.lon]}
          icon={numberedIcon(number, restaurant.id === highlightedId)}
          title={restaurant.name}
          eventHandlers={{ click: () => onSelectRestaurant(restaurant.id) }}
        />
      ))}
      <FitToContent origin={origin} restaurants={restaurants} />
      {onPickOrigin && <ClickToPick onPick={onPickOrigin} />}
    </MapContainer>
  )
}
