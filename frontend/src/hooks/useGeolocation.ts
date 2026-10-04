import { useEffect, useState } from 'react'

import type { Location } from '../api/types'

export type GeolocationState =
  | { status: 'locating' }
  | { status: 'located'; location: Location }
  | { status: 'unavailable'; reason: string }

/**
 * Ask the browser for the visitor's position once, when the component first appears.
 * The browser shows its own permission prompt; the result arrives later in a callback.
 */
export function useGeolocation(): GeolocationState {
  const supported = 'geolocation' in navigator
  const [state, setState] = useState<GeolocationState>(() =>
    supported
      ? { status: 'locating' }
      : { status: 'unavailable', reason: 'This browser cannot share its location.' },
  )

  useEffect(() => {
    if (!supported) return
    navigator.geolocation.getCurrentPosition(
      (position) =>
        setState({
          status: 'located',
          location: { lat: position.coords.latitude, lon: position.coords.longitude },
        }),
      (error) =>
        setState({
          status: 'unavailable',
          reason:
            error.code === error.PERMISSION_DENIED
              ? 'Location access is blocked.'
              : 'Your location could not be found.',
        }),
      // A rough position is plenty for a 2 km search, and a five-minute-old one is fine.
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    )
  }, [supported])

  return state
}
