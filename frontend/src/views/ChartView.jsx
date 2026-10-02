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
  { id: 'genres', label: 'Genres', icon: '🎨' },
]

const GENRE_EMOJI = [
  [/(rock|metal|punk)/, '🎸'],
  [/(hip|rap|trap|drill)/, '🎤'],
  [/(electro|dance|house|techno|trance|ambient|dubstep)/, '🎛️'],
  [/(pop)/, '🍬'],
  [/(jazz|blues|swing)/, '🎷'],
  [/(classical|orchest|opera|piano)/, '🎻'],
  [/(indie|alternative|alt)/, '🌙'],
  [/(r\/?b|soul|funk|groove)/, '🕺'],
  [/(folk|acoustic|singer)/, '🪕'],
  [/(latin|reggaeton|salsa|reggae)/, '💃'],
  [/(k-pop|j-pop|asian)/, '🌸'],
  [/(lofi|lo-fi|chill)/, '🌃'],
]

const genreEmoji = (name) =>
  (GENRE_EMOJI.find(([re]) => re.test(name.toLowerCase())) || [null, '🎧'])[1]

export default function ChartView() {
  const { me, toast, rev, refreshAll, refreshMe } = useApp()
  const [tab, setTab] = useState('trending')
  const [songs, setSongs] = useState(null)
  const [genres, setGenres] = useState(null)
  const [genre, setGenre] = useState(null) // selected genre name
  const [genreSongs, setGenreSongs] = useState(null)
  const [addSong, setAddSong] = useState(null)
  const [pinnedBusy, setPinnedBusy] = useState(false)

  const prevTab = useRef(tab)
  useEffect(() => {
    let cancelled = false
    if (prevTab.current !== tab) {
      prevTab.current = tab
      setSongs(null) // skeleton only when switching tabs
      if (tab === 'genres') setGenreSongs(null)
    }
    const load = () => {
      if (tab === 'genres' && genre) {
        api
          .get('/songs', { params: { tab: 'top', genre } })
          .then((r) => !cancelled && setGenreSongs(r.data.songs))
          .catch(() => !cancelled && setGenreSongs((s) => s ?? []))
      } else if (tab === 'genres') {
        api
          .get('/songs/genres')
          .then((r) => !cancelled && setGenres(r.data))
          .catch(() => !cancelled && setGenres([]))
      } else {
        api
          .get('/songs', { params: { tab } })
          .then((r) => !cancelled && setSongs(r.data.songs))
          .catch(() => !cancelled && setSongs((s) => s ?? []))
      }
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
  }, [tab, genre, rev])

  const switchTab = (id) => {
    haptic('light')
    setTab(id)
    setGenre(null)
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

  const list = tab === 'genres' ? genreSongs : songs
  const loading =
    tab === 'genres' ? (genre ? genreSongs === null : genres === null) : songs === null
  const countLabel =
    tab === 'genres'
      ? genre && genreSongs
        ? `${genreSongs.length} track${genreSongs.length === 1 ? '' : 's'}`
        : genres
        ? `${genres.length} genre${genres.length === 1 ? '' : 's'}`
        : ''
      : songs
      ? `${songs.length} track${songs.length === 1 ? '' : 's'}`
      : ''

  const renderSongs = () =>
    list.length === 0 ? (
      <div className="glass rounded-3xl p-10 text-center">
        <div className="text-4xl mb-3">💿</div>
        <div className="font-bold">
          {tab === 'genres' && genre ? `No songs in “${genre}” yet` : 'Nothing on the chart yet'}
        </div>
        <p className="text-xs text-base-content/50 mt-1">
          Send an MP3 in the Persona group — PersonaBot will put it here
          instantly.
        </p>
      </div>
    ) : (
      <div className="space-y-3">
        {list.map((song, i) => (
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
    )

  const renderGenres = () =>
    genres.length === 0 ? (
      <div className="glass rounded-3xl p-10 text-center">
        <div className="text-4xl mb-3">🎨</div>
        <div className="font-bold">No genres yet</div>
        <p className="text-xs text-base-content/50 mt-1">
          Genres arrive automatically with last.fm data for each new song.
        </p>
      </div>
    ) : (
      <div className="grid grid-cols-2 gap-3">
        {genres.map((g) => (
          <button
            key={g.name}
            onClick={() => {
              haptic('light')
              setGenreSongs(null)
              setGenre(g.name)
            }}
            className="glass rounded-2xl p-4 text-left shadow-card transition-transform active:scale-[0.98] hover:border-primary/40 border border-transparent"
          >
            <div className="text-2xl">{genreEmoji(g.name)}</div>
            <div className="font-bold text-sm truncate mt-1.5 capitalize">
              {g.name}
            </div>
            <div className="text-[10px] text-base-content/40 mt-0.5">
              {g.count} track{g.count === 1 ? '' : 's'}
            </div>
          </button>
        ))}
      </div>
    )

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
              <span className="text-xs">{t.icon}</span>
              {t.label}
            </button>
          ))}
        </div>

        {tab === 'genres' && genre && (
          <div className="flex items-center gap-2 mb-3">
            <button
              className="btn btn-xs btn-ghost rounded-xl text-primary px-2"
              onClick={() => {
                haptic('light')
                setGenre(null)
              }}
            >
              ← All genres
            </button>
            <div className="text-sm font-extrabold capitalize">
              {genreEmoji(genre)} {genre}
              <span className="text-[10px] font-bold text-base-content/40 ml-2">
                sorted by rating
              </span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <span className="loading loading-bars loading-md text-primary" />
          </div>
        ) : tab === 'genres' && !genre ? (
          renderGenres()
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
