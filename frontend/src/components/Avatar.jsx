import React from 'react'
import { avatarGradient, displayName, initials } from '../lib/format'

export default function Avatar({ user, size = 10, className = '', ring = false }) {
  const dim = { size: `${size * 0.25}rem`, minWidth: `${size * 0.25}rem` }
  return (
    <div
      title={displayName(user)}
      style={dim}
      className={`avatar placeholder ${ring ? 'ring-2 ring-primary/60 ring-offset-2 ring-offset-base-100' : ''} ${className}`}
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
