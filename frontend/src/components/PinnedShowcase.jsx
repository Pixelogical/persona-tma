import React, { useEffect, useState } from 'react'
import api from '../lib/api'
import { displayName, timeAgo } from '../lib/format'
import { openLink } from '../lib/telegram'
import Avatar from './Avatar'
import { StarsDisplay } from './StarRating'

export default function PinnedShowcase({ rev, onRefresh }) {
  const [pins, setPins] = useState([])
  const [removing, setRemoving] = useState(null)

  const load = () => api.get('/pins').then((r) => setPins(r.data)).catch(() => {})
  useEffect(() => {
    load()
  }, [rev])

  if (!pins.length) return null

  const unpin = async (id) => {
    setRemoving(id)
    try {
      await api.delete(`/pins/${id}`)
      await load()
      onRefresh?.()
    } catch {
      /* toast handled upstream */
    } finally {
      setRemoving(null)
    }
  }

  return (
    <section className="px-4 fade-up">
      <h2 className="text-sm font-bold tracking-wide text-base-content/70 uppercase mb-2">
        📌 Pinned by the Top Voters
      </h2>
      <div className="flex gap-3 overflow-x-auto no-scrollbar pb-1 -mx-4 px-4 snap-x">
        {pins.map((pin) => (
          <div
            key={pin.id}
            className="pin-card glass rounded-3xl p-4 min-w-[260px] max-w-[280px] snap-start border border-warning/25"
          >
            <div className="flex items-start justify-between">
              <span className="badge badge-sm badge-warning badge-outline gap-1 text-[10px] font-bold uppercase">
                📌 pinned pick
              </span>
            </div>
            <button
              className="block w-full text-left mt-2 group"
              onClick={() => openLink(pin.link)}
              title="Open this song in Telegram"
            >
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-warning/30 to-secondary/30 border border-warning/20 flex items-center justify-center text-lg shrink-0">
                  🎵
                </div>
                <div className="min-w-0">
                  <div className="font-bold text-sm truncate group-hover:text-warning transition-colors">
                    {pin.song.title}
                  </div>
                  <div className="text-xs text-base-content/50 truncate">
                    {pin.song.artist || 'Unknown artist'}
                  </div>
                </div>
              </div>
            </button>
            <div className="flex items-center justify-between mt-3">
              <StarsDisplay value={pin.song.avg} />
              <span className="text-[10px] text-base-content/40">
                {pin.song.votes} vote{pin.song.votes === 1 ? '' : 's'}
              </span>
            </div>
            <div className="divider my-2 py-0 opacity-20" />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 min-w-0">
                <Avatar user={pin.pinned_by} size={7} />
                <div className="min-w-0">
                  <div className="text-[11px] font-bold truncate">
                    {displayName(pin.pinned_by)}
                  </div>
                  <div className="text-[9px] text-base-content/40">
                    pinned {timeAgo(pin.created_at)}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  className="btn btn-xs btn-circle btn-ghost text-warning"
                  onClick={() => openLink(pin.link)}
                  title="Open in Telegram"
                >
                  ↗
                </button>
                {pin.can_remove && (
                  <button
                    className="btn btn-xs btn-circle btn-ghost text-error"
                    disabled={removing === pin.id}
                    onClick={() => unpin(pin.id)}
                    title="Remove my pin"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
