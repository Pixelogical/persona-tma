import React, { useEffect, useRef, useState } from 'react'
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
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)

  const searching = query.trim().length > 0

  useEffect(() => {
    const q = query.trim()
    if (!q) {
      setResults(null)
      return undefined
    }
    let cancelled = false
    setResults(null)
    // debounce so we don't hit the API on every keystroke
    const timer = setTimeout(() => {
      api
        .get('/songs/search', { params: { q } })
        .then((r) => !cancelled && setResults(r.data.songs))
        .catch(() => !cancelled && setResults([]))
    }, 300)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [query, rev])

  const prevTab = useRef(tab)
  useEffect(() => {
    let cancelled = false
    if (prevTab.current !== tab) {
      prevTab.current = tab
      setSongs(null) // skeleton only when switching tabs
    }
    const load = () => {
      api
        .get('/songs', { params: { tab } })
        .then((r) => !cancelled && setSongs(r.data.songs))
        .catch(() => !cancelled && setSongs((s) => s ?? []))
    }
    load()
    // poll so tracks shared in the group appear without a manual refresh
    const timer = setInterval(() => {
      if (!document.hidden) load()
    }, 15000)
    const onVisible = () => !document.hidden && load()
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      cancelled = true
      clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [tab, rev])

  const switchTab = (id) => {
    haptic('light')
    setTab(id)
  }

  const handleVote = async (song, stars) => {
    const { data } = await api.post(`/songs/${song.id}/vote`, { value: stars })
    toast(
      data.gained
        ? `⭐ Voted ${stars}★ · +1 point → ${data.points} total`
        : `⭐ Updated to ${stars}★ — re-rating already-rated songs earns no point`,
      'success'
    )
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

  const countLabel = songs ? `${songs.length} track${songs.length === 1 ? '' : 's'}` : ''

  const renderCards = (list, withRank) => (
    <div className="space-y-3">
      {list.map((song, i) => (
        <SongCard
          key={song.id}
          song={song}
          rank={withRank ? i + 1 : undefined}
          isTop3={!!me?.is_top3}
          onVote={handleVote}
          onAdd={setAddSong}
          onPin={handlePin}
        />
      ))}
    </div>
  )

  const renderSongs = () =>
    songs.length === 0 ? (
      <div className="glass rounded-3xl p-10 text-center">
        <div className="text-4xl mb-3">💿</div>
        <div className="font-bold">Nothing on the chart yet</div>
        <p className="text-xs text-base-content/50 mt-1">
          Send an MP3 in the Persona group — PersonaBot will put it here
          instantly.
        </p>
      </div>
    ) : (
      renderCards(songs, true)
    )

  const searchBar = (
    <div className="relative">
      <span className="absolute inset-y-0 left-3.5 flex items-center text-sm opacity-50">
        🔍
      </span>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search songs or artists…"
        dir="auto"
        className="input input-bordered w-full rounded-2xl bg-base-200/80 border-base-content/10 pl-10 pr-10 text-sm focus:border-primary/50"
      />
      {query && (
        <button
          className="btn btn-xs btn-circle btn-ghost absolute inset-y-0 right-2 my-auto h-6 w-6"
          title="Clear"
          onClick={() => setQuery('')}
        >
          ✕
        </button>
      )}
    </div>
  )

  if (searching) {
    return (
      <div className="px-4 pt-4 fade-up pb-28 space-y-4">
        {searchBar}
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold tracking-wide text-base-content/70 uppercase">
            Search results
          </h2>
          {results && (
            <span className="text-[10px] text-base-content/40">
              {results.length} match{results.length === 1 ? '' : 'es'}
            </span>
          )}
        </div>
        {results === null ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <span className="loading loading-bars loading-md text-primary" />
          </div>
        ) : results.length === 0 ? (
          <div className="glass rounded-3xl p-10 text-center">
            <div className="text-4xl mb-3">🔍</div>
            <div className="font-bold">No songs match “{query.trim()}”</div>
            <p className="text-xs text-base-content/50 mt-1">
              Try fewer words — both title and artist are searched.
            </p>
          </div>
        ) : (
          renderCards(results, false)
        )}
        {addSong && (
          <AddToPlaylist song={addSong} onClose={() => setAddSong(null)} />
        )}
      </div>
    )
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
          <span className="text-[10px] text-base-content/40">{countLabel}</span>
        </div>

        <div className="mb-4">{searchBar}</div>

        <div
          role="tablist"
          className="tabs tabs-boxed bg-base-200/80 border border-base-content/5 p-1 mb-4"
        >
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              onClick={() => switchTab(t.id)}
              className={`tab gap-1 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                tab === t.id
                  ? 'tab-active bg-gradient-to-r from-primary to-secondary text-white shadow-glow'
                  : 'text-base-content/50'
              }`}
            >
              <span className="text-xs"></span>
              {t.label}
            </button>
          ))}
        </div>

        {songs === null ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <span className="loading loading-bars loading-md text-primary" />
          </div>
        ) : (
          renderSongs()
        )}
      </section>

      {addSong && (
        <AddToPlaylist song={addSong} onClose={() => setAddSong(null)} />
      )}
    </div>
  )
}
