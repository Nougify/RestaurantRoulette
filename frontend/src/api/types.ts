// TypeScript descriptions of the JSON the Flask API sends and accepts. They exist only at
// compile time: they catch typos such as `restaurant.adress` before the code ever runs.

export type Category = 'restaurant' | 'cafe' | 'fast_food'
export type Diet = 'vegetarian' | 'vegan' | 'halal' | 'kosher' | 'gluten_free'

export interface Location {
  lat: number
  lon: number
}

export interface Restaurant extends Location {
  id: number
  name: string
  category: Category
  cuisines: string[]
  diets: Diet[]
  opening_hours: string | null
  // null when the hours are missing or unreadable.
  open_now: boolean | null
  address: string | null
  phone: string | null
  website: string | null
  // Only present on search results, which are measured from a point.
  distance_m?: number
}

export interface FilterOptions {
  categories: Category[]
  diets: Diet[]
  cuisines: { name: string; count: number }[]
  radius: { default: number; max: number }
  max_spin_count: number
}

export interface SearchFilters {
  radius: number
  categories: Category[]
  cuisines: string[]
  diets: Diet[]
  dietMatch: 'all' | 'any'
  openNow: boolean
}

export interface User {
  id: number
  email: string
}

export interface Session {
  token: string
  user: User
}

export interface Credentials {
  email: string
  password: string
}

export interface FieldError {
  field: string
  message: string
}
