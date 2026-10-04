const LABELS: Record<string, string> = {
  fast_food: 'Fast food',
  cafe: 'Café',
  gluten_free: 'Gluten-free',
}

/** Turn an API value such as "coffee_shop" into "Coffee shop" for display. */
export function label(value: string): string {
  if (value in LABELS) return LABELS[value]
  const words = value.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** 850 → "850 m", 1234 → "1.2 km", 2000 → "2 km". */
export function formatDistance(metres: number): string {
  if (metres < 1000) return `${Math.round(metres)} m`
  return `${(metres / 1000).toFixed(1).replace(/\.0$/, '')} km`
}
