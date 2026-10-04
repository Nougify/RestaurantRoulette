interface ChipProps {
  label: string
  selected: boolean
  onToggle: () => void
}

/** A pill-shaped toggle button used for every multi-choice filter. */
export function Chip({ label, selected, onToggle }: ChipProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      className={`rounded-full border px-3 py-1 text-sm transition-colors ${
        selected
          ? 'border-accent bg-accent text-white'
          : 'border-zinc-300 bg-white text-zinc-700 hover:border-zinc-400'
      }`}
    >
      {label}
    </button>
  )
}
