import React, { useEffect, useState } from 'react'
import api from '../lib/api'
import { useApp } from '../store'
import { displayName } from '../lib/format'
import Avatar from './Avatar'

const STYLES = {
  1: { ring: 'ring-warning/70', text: 'text-warning', order: 'order-2', h: 'h-16', crown: '👑' },
  2: { ring: 'ring-base-content/30', text: 'text-base-content/80', order: 'order-1', h: 'h-11', crown: '🥈' },
  3: { ring: 'ring-orange-400/50', text: 'text-orange-300', order: 'order-3', h: 'h-8', crown: '🥉' },
}

export default function Leaderboard({ rev, me }) {
  const { openProfile } = useApp()
  const [entries, setEntries] = useState([])

  useEffect(() => {
    api.get('/users/top').then((r) => setEntries(r.data)).catch(() => {})
  }, [rev])

  if (!entries.length) return null

  return (
    <section className="px-4 fade-up">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-bold tracking-wide text-base-content/70 uppercase">
          Top Voters
        </h2>
        <span className="text-[10px] text-base-content/40">
          1 vote = 1 point
        </span>
      </div>
      <div className="glass rounded-3xl p-4 shadow-card">
        <div className="flex items-end justify-center gap-3">
          {entries.map((e) => {
            const st = STYLES[e.rank] || STYLES[3]
            return (
              <div
                key={e.user.id}
                className={`${st.order} flex flex-col items-center gap-1.5 w-1/3`}
              >
                <div className="text-base leading-none">{st.crown}</div>
                <button
                  className="relative cursor-pointer"
                  onClick={() => openProfile(e.user.id)}
                  title="View profile"
                >
                  <Avatar user={e.user} size={e.rank === 1 ? 14 : 12} className={`rounded-full ring-2 ${st.ring} ring-offset-2 ring-offset-base-200`} />
                </button>
                <div className="text-xs font-bold truncate max-w-full px-1">
                  {displayName(e.user)}
                </div>
                <div className={`text-[11px] font-extrabold ${st.text}`}>
                  {e.user.points} pts
                </div>
                <div className={`w-full rounded-t-xl bg-gradient-to-b from-base-300 to-base-200 border border-b-0 border-base-content/5 ${st.h}`} />
              </div>
            )
          })}
        </div>
        {me && !entries.some((e) => e.user.id === me.id) && me.rank && (
          <div className="text-center text-[11px] text-base-content/50 mt-3">
            You are #{me.rank} — keep voting to join the podium
          </div>
        )}
      </div>
    </section>
  )
}
