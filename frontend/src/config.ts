import type { Location } from './api/types'

// Where the Flask API runs. Vite exposes only variables prefixed VITE_ to browser code,
// and they are baked in at build time, so the deployed build is given the real URL.
export const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

// Downtown Vancouver: where the map starts before the visitor's location is known.
export const DEFAULT_CENTER: Location = { lat: 49.2827, lon: -123.1207 }

// The data covers Metro Vancouver only. A location further than this from its centre
// gets no results, so the visitor is asked to pick a point on the map instead.
export const COVERAGE_CENTER: Location = { lat: 49.22, lon: -122.95 }
export const COVERAGE_RADIUS_M = 45_000
