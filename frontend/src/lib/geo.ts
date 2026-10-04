import type { Location } from '../api/types'
import { COVERAGE_CENTER, COVERAGE_RADIUS_M } from '../config'

const EARTH_RADIUS_M = 6_371_000

/**
 * Straight-line distance over the earth's surface (the haversine formula). Only used for
 * the rough "is this inside Metro Vancouver" check; real searches use PostGIS.
 */
export function distanceMetres(a: Location, b: Location): number {
  const toRadians = (degrees: number) => (degrees * Math.PI) / 180
  const dLat = toRadians(b.lat - a.lat)
  const dLon = toRadians(b.lon - a.lon)
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRadians(a.lat)) * Math.cos(toRadians(b.lat)) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h))
}

export function isInCoverage(location: Location): boolean {
  return distanceMetres(location, COVERAGE_CENTER) <= COVERAGE_RADIUS_M
}
