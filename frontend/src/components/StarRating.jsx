import React, { useState } from 'react'
import { haptic } from '../lib/telegram'

function Star({ filled, size }) {
  return (
    <svg
      viewBox="0 0 24 24"
      style={{ width: size, height: size }}
      className={filled ? 'text-warning drop-shadow-[0_0_6px_rgba(229,169,61,0.6)]' : 'text-base-content/20'}
      fill="currentColor"
    >
      <path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
    </svg>
  )
}

/** Read-only average display (supports fractional fill) */
export function StarsDisplay({ value = 0, size = 13 }) {
  const pct = Math.max(0, Math.min(100, (value / 5) * 100))
  return (
    <span className="relative inline-flex" style={{ lineHeight: 0 }}>
      <span className="inline-flex">
        {[...Array(5)].map((_, i) => (
          <Star key={i} filled={false} size={size} />
        ))}
      </span>
      <span
        className="absolute left-0 top-0 inline-flex overflow-hidden"
        style={{ width: `${pct}%` }}
      >
        {[...Array(5)].map((_, i) => (
          <Star key={i} filled size={size} />
        ))}
      </span>
    </span>
  )
}

/** Interactive 5-star voting */
export default function StarRating({ value, onVote, disabled = false }) {
  const [hover, setHover] = useState(0)
  const shown = hover || value || 0
  return (
    <div
      className="stars-select inline-flex items-center gap-0.5"
      onTouchEnd={() => setHover(0)}
    >
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          disabled={disabled}
          aria-label={`Rate ${star} star${star > 1 ? 's' : ''}`}
          onMouseEnter={() => !disabled && setHover(star)}
          onMouseLeave={() => setHover(0)}
          onClick={(e) => {
            e.stopPropagation()
            if (disabled || value === star) return
            haptic('light')
            onVote(star)
          }}
          className="p-0.5 rounded touch-manipulation disabled:opacity-60"
        >
          <Star filled={star <= shown} size={19} />
        </button>
      ))}
    </div>
  )
}
