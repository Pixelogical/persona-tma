import React, { useState } from 'react'
import { avatarGradient, displayName, initials } from '../lib/format'

export default function Avatar({ user, size = 10, className = '', ring = false }) {
  const dim = { size: `${size * 0.25}rem`, minWidth: `${size * 0.25}rem` }
  const [broken, setBroken] = useState(false)
  const ringCls = ring ? 'ring-2 ring-primary/60 ring-offset-2 ring-offset-base-100' : ''

  if (user?.avatar && !broken) {
    return (
      <div
        title={displayName(user)}
        style={dim}
        className={`avatar ${ringCls} ${className}`}
      >
        <div className="w-full rounded-full border border-base-content/10" style={dim}>
          <img
            src={user.avatar}
            alt={displayName(user)}
            loading="lazy"
            onError={() => setBroken(true)}
            className="w-full h-full object-cover rounded-full"
          />
        </div>
      </div>
    )
  }

  return (
    <div
      title={displayName(user)}
      style={dim}
      className={`avatar placeholder ${ringCls} ${className}`}
    >
      <div
        className={`w-full rounded-full bg-gradient-to-br ${avatarGradient(user)} text-white flex items-center justify-center font-extrabold select-none`}
        style={{ fontSize: `${Math.max(size * 2.6, 9)}px` }}
      >
        <span className="leading-none">{initials(user)}</span>
      </div>
    </div>
  )
}
