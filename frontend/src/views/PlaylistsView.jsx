import React, { useEffect, useState } from 'react'
import api, { errMessage } from '../lib/api'
import { displayName } from '../lib/format'
import { haptic } from '../lib/telegram'
import { useApp } from '../store'
import Avatar from '../components/Avatar'
import PlaylistDetail from '../components/PlaylistDetail'
import { StarsDisplay } from '../components/StarRating'

export default function PlaylistsView() {
  const { toast, rev, refreshAll } = useApp()
  const [playlists, setPlaylists] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [playBusy, setPlayBusy] = useState(null)

  useEffect(() => {
    api
      .get('/playlists')
      .then((r) => setPlaylists(r.data))
      .catch(() => setPlaylists([]))
  }, [rev])

  const create = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    try {
      const { data } = await api.post('/playlists', { name: name.trim() })
      toast('Playlist created — it is public for everyone 🎉', 'success')
      setName('')
      setCreateOpen(false)
      refreshAll()
      setOpenId(data.id)
    } catch (err) {
      toast(errMessage(err), 'error')
    } finally {
      setCreating(false)
    }
  }

  const quickPlay = async (pl) => {
    if (playBusy) return
    if (!pl.song_count) {
      toast('That playlist is empty', 'warning')
      return
    }
    setPlayBusy(pl.id)
    haptic('medium')
    try {
      const { data } = await api.post(`/playlists/${pl.id}/play`)
      toast(
        `▶️ “${data.playlist}” is playing in the group — ${data.started} track(s)`,
        'success'
      )
    } catch (e) {
      toast(errMessage(e), 'error')
    } finally {
      setPlayBusy(null)
    }
  }

  return (
    <div className="px-4 pb-28 space-y-4 fade-up">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold tracking-wide text-base-content/70 uppercase">
            Playlists
          </h2>
          <p className="text-[10px] text-base-content/40 mt-0.5">
            Public to the whole group — press play and the bot streams it into
            the chat
          </p>
        </div>
        <button
          className="btn btn-sm btn-primary rounded-xl px-4 shadow-glow"
          onClick={() => setCreateOpen(true)}
        >
          + New
        </button>
      </div>

      {playlists === null ? (
        <div className="flex justify-center py-16">
          <span className="loading loading-bars loading-md text-primary" />
        </div>
      ) : playlists.length === 0 ? (
        <div className="glass rounded-3xl p-10 text-center">
          <div className="text-4xl mb-3">🗂️</div>
          <div className="font-bold">No playlists yet</div>
          <p className="text-xs text-base-content/50 mt-1">
            Create one and collect your favourite tracks from the chart.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          {playlists.map((pl) => (
            <div
              key={pl.id}
              className="glass rounded-3xl p-4 shadow-card flex flex-col gap-3 active:scale-[0.98] transition-transform"
            >
              <button
                className="text-left min-w-0"
                onClick={() => {
                  haptic('light')
                  setOpenId(pl.id)
                }}
              >
                <div className="w-full aspect-square max-h-28 rounded-2xl bg-gradient-to-br from-primary/50 via-secondary/40 to-accent/30 border border-white/5 flex items-center justify-center text-4xl mb-2.5 shadow-inner">
                  🎶
                </div>
                <div className="font-bold text-sm truncate">{pl.name}</div>
                <div className="flex items-center gap-1.5 mt-1">
                  <Avatar user={pl.owner} size={5} />
                  <span className="text-[10px] text-base-content/45 truncate">
                    {displayName(pl.owner)}
                    {pl.is_mine ? ' · you' : ''}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] text-base-content/40">
                    {pl.song_count} track{pl.song_count === 1 ? '' : 's'}
                  </span>
                  {pl.avg > 0 && <StarsDisplay value={pl.avg} size={9} />}
                </div>
              </button>
              <button
                onClick={() => quickPlay(pl)}
                disabled={playBusy === pl.id}
                className="btn btn-sm btn-circle bg-gradient-to-br from-primary to-secondary border-0 text-white self-end shadow-glow"
                title="Play in group chat"
              >
                {playBusy === pl.id ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      {createOpen && (
        <div className="modal modal-open">
          <form onSubmit={create} className="modal-box glass border border-base-content/10 max-w-sm">
            <h3 className="font-bold text-lg">New playlist</h3>
            <p className="text-xs text-base-content/50 mt-1 mb-3">
              Playlists are public — every member can listen to them.
            </p>
            <input
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Late night drive"
              maxLength={60}
              className="input input-bordered input-sm w-full bg-base-300/60 border-base-content/10 rounded-xl"
            />
            <div className="modal-action">
              <button
                type="button"
                className="btn btn-sm btn-ghost rounded-xl"
                onClick={() => setCreateOpen(false)}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating || !name.trim()}
                className="btn btn-sm btn-primary rounded-xl px-5"
              >
                {creating ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  'Create'
                )}
              </button>
            </div>
          </form>
          <div className="modal-backdrop pointer-events-none" />
        </div>
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
