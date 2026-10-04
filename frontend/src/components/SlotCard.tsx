import { useEffect, useState } from 'react'

const TICK_MS = 70

interface SlotCardProps {
  number: number
  // Names to flick through while the reel spins.
  reel: string[]
}

/**
 * A placeholder card shown during a spin: it cycles through names like a slot-machine reel.
 * Each card starts at a different point in the reel so they do not move in lockstep.
 */
export function SlotCard({ number, reel }: SlotCardProps) {
  const [position, setPosition] = useState(number * 7)

  useEffect(() => {
    const timer = setInterval(() => setPosition((current) => current + 1), TICK_MS)
    // The cleanup function runs when the card disappears, so the interval never leaks.
    return () => clearInterval(timer)
  }, [])

  const name = reel.length > 0 ? reel[position % reel.length] : '…'

  return (
    <div className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white p-4">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-sm font-semibold text-white">
        {number}
      </span>
      <div className="h-6 flex-1 overflow-hidden">
        <p key={position} className="animate-reel truncate font-semibold text-zinc-400">
          {name}
        </p>
      </div>
    </div>
  )
}
