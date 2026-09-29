import React, { useEffect, useState } from 'react'
import api from '../lib/api'
import { displayName, timeAgo } from '../lib/format'
import { isTMA } from '../lib/telegram'
import { useApp } from '../store'
import Avatar from '../components/Avatar'
import PlaylistDetail from '../components/PlaylistDetail'

const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' }

export default function ProfileView() {
  const { me, logout, rev } = useApp()
  const [playlists, setPlaylists] = useState([])
  const [openId, setOpenId] = useState(null)

  useEffect(() => {
    api
      .get('/playlists')
      .then((r) => setPlaylists(r.data.filter((p) => p.is_mine)))
      .catch(() => {})
  }, [rev])

  if (!me) return null

  return (
    <div className="px-4 pb-28 space-y-5 fade-up">
      <div className="glass rounded-3xl p-6 shadow-card text-center relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/20 to-transparent pointer-events-none" />
        <div className="relative">
          <div className="flex justify-center">
            <Avatar user={me} size={22} ring />
          </div>
          <h2 className="text-xl font-black mt-3">{displayName(me)}</h2>
          {me.username && (
            <p className="text-xs text-base-content/50">@{me.username}</p>
          )}
          {me.rank && (
            <div className="badge badge-sm gap-1 mt-2 bg-base-300/70 border-base-content/10 font-bold">
              {MEDALS[me.rank] || '🎯'} Rank #{me.rank}
              {me.is_top3 && (
                <span className="text-warning">· Pin power unlocked 📌</span>
              )}
            </div>
          )}

          <div className="grid grid-cols-3 gap-2 mt-5">
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-br from-primary to-secondary">
                {me.points}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Points
              </div>
            </div>
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black">{me.votes_count}</div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Votes
              </div>
            </div>
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black">{me.pins_count}</div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Pins
              </div>
            </div>
          </div>
          <p className="text-[10px] text-base-content/35 mt-3">
            Member since {timeAgo(me.created_at)} · every vote you cast earns 1
            point
          </p>
        </div>
      </div>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-bold tracking-wide text-base-content/70 uppercase">
            My Playlists
          </h3>
          <span className="text-[10px] text-base-content/40">public</span>
        </div>
        {playlists.length === 0 ? (
          <div className="glass rounded-3xl p-8 text-center text-sm text-base-content/50">
            You have no playlists yet — add songs from the chart with the +
            button.
          </div>
        ) : (
          <div className="space-y-2">
            {playlists.map((pl) => (
              <button
                key={pl.id}
                onClick={() => setOpenId(pl.id)}
                className="w-full glass rounded-2xl p-3.5 flex items-center gap-3 text-left active:scale-[0.99] transition-transform"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/50 to-secondary/50 flex items-center justify-center">
                  🎶
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold truncate">{pl.name}</div>
                  <div className="text-[10px] text-base-content/40">
                    {pl.song_count} track{pl.song_count === 1 ? '' : 's'} ·{' '}
                    created {timeAgo(pl.created_at)}
                  </div>
                </div>
                <span className="text-base-content/30">→</span>
              </button>
            ))}
          </div>
        )}
      </section>

      {!isTMA() && (
        <button className="btn btn-sm btn-ghost text-error rounded-xl w-full" onClick={logout}>
          Sign out
        </button>
      )}

      {openId && (
        <PlaylistDetail
          playlistId={openId}
          onClose={() => setOpenId(null)}
          onDeleted={() => setOpenId(null)}
        />
      )}
    </div>
  )
}
