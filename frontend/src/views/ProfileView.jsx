import React, { useEffect, useState } from 'react'
import api from '../lib/api'
import { timeAgo } from '../lib/format'
import { isTMA } from '../lib/telegram'
import { useApp } from '../store'
import ProfileSheet from '../components/ProfileSheet'
import PlaylistDetail from '../components/PlaylistDetail'

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
      <ProfileSheet userId={me.id} rev={rev} />

      {(me.rank || me.votes_count || me.pins_count) > 0 && (
        <div className="glass rounded-2xl px-4 py-2.5 flex items-center justify-center gap-2 text-[11px] font-bold text-base-content/60 flex-wrap">
          {me.rank && <span>🎯 Rank #{me.rank}</span>}
          {me.is_top3 && <span className="text-warning">· 📌 Pin power unlocked</span>}
          <span>· 🗳 {me.votes_count} votes cast</span>
          <span>· 📌 {me.pins_count} pins</span>
        </div>
      )}

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
