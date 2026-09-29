import React, { useEffect, useState } from 'react'
import api, { errMessage } from '../lib/api'
import { useApp } from '../store'
import { haptic } from '../lib/telegram'
import AddToPlaylist from '../components/AddToPlaylist'
import Leaderboard from '../components/Leaderboard'
import PinnedShowcase from '../components/PinnedShowcase'
import SongCard from '../components/SongCard'

const TABS = [
  { id: 'trending', label: 'Trending', icon: '🔥' },
  { id: 'new', label: 'New', icon: '✨' },
  { id: 'top', label: 'Top', icon: '🏆' },
]

export default function ChartView() {
  const { me, toast, rev, refreshAll, refreshMe } = useApp()
  const [tab, setTab] = useState('trending')
  const [songs, setSongs] = useState(null)
  const [addSong, setAddSong] = useState(null)
  const [pinnedBusy, setPinnedBusy] = useState(false)

  useEffect(() => {
    let cancelled = false
    if (!songs) setSongs(null)
    api
      .get('/songs', { params: { tab } })
      .then((r) => !cancelled && setSongs(r.data.songs))
      .catch(() => !cancelled && setSongs([]))
    return () => {
      cancelled = true
    }
  }, [tab, rev])

  const handleVote = async (song, stars) => {
    const { data } = await api.post(`/songs/${song.id}/vote`, { value: stars })
    toast(`⭐ Voted ${stars}★ · +1 point → ${data.points} total`, 'success')
    refreshMe()
    refreshAll()
  }

  const handlePin = async (song) => {
    if (pinnedBusy) return
    setPinnedBusy(true)
    try {
      await api.post('/pins', { song_id: song.id })
      toast(`📌 “${song.title}” pinned for everyone`, 'success')
      haptic('success')
      refreshAll()
    } catch (e) {
      toast(errMessage(e, 'Only the top 3 voters can pin'), 'error')
      haptic('error')
    } finally {
      setPinnedBusy(false)
    }
  }

  return (
    <div className="space-y-5 pb-28">
      <PinnedShowcase rev={rev} />
      <Leaderboard rev={rev} me={me} />

      <section className="px-4 fade-up">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-bold tracking-wide text-base-content/70 uppercase">
            The Chart
          </h2>
          <span className="text-[10px] text-base-content/40">
            {songs ? `${songs.length} track${songs.length === 1 ? '' : 's'}` : ''}
          </span>
        </div>

        <div
          role="tablist"
          className="tabs tabs-boxed bg-base-200/80 border border-base-content/5 p-1 mb-4"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              onClick={() => {
                haptic('light')
                setTab(t.id)
              }}
              className={`tab gap-1.5 rounded-xl text-sm font-bold transition-all ${
                tab === t.id
                  ? 'tab-active bg-gradient-to-r from-primary to-secondary text-white shadow-glow'
                  : 'text-base-content/50'
              }`}
            >
              <span className="text-xs">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {songs === null ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <span className="loading loading-bars loading-md text-primary" />
          </div>
        ) : songs.length === 0 ? (
          <div className="glass rounded-3xl p-10 text-center">
            <div className="text-4xl mb-3">💿</div>
            <div className="font-bold">Nothing on the chart yet</div>
            <p className="text-xs text-base-content/50 mt-1">
              Send an MP3 in the Persona group — PersonaBot will put it here
              instantly.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {songs.map((song, i) => (
              <SongCard
                key={song.id}
                song={song}
                rank={i + 1}
                isTop3={!!me?.is_top3}
                onVote={handleVote}
                onAdd={setAddSong}
                onPin={handlePin}
              />
            ))}
          </div>
        )}
      </section>

      {addSong && (
        <AddToPlaylist song={addSong} onClose={() => setAddSong(null)} />
      )}
    </div>
  )
}
