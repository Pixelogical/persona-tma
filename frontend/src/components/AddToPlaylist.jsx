import React, { useEffect, useState } from 'react'
import api, { errMessage } from '../lib/api'
import { useApp } from '../store'
import PlaylistDetail from './PlaylistDetail'

export default function AddToPlaylist({ song, onClose }) {
  const { toast, refreshAll } = useApp()
  const [playlists, setPlaylists] = useState(null)
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [openId, setOpenId] = useState(null)

  const load = () => api.get('/playlists').then((r) => setPlaylists(r.data))

  useEffect(() => {
    load().catch(() => setPlaylists([]))
  }, [])

  const add = async (plId) => {
    try {
      await api.post(`/playlists/${plId}/songs`, { song_id: song.id })
      toast(`Added “${song.title}” to playlist`, 'success')
      refreshAll()
      await load()
    } catch (e) {
      toast(errMessage(e), 'error')
    }
  }

  const create = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    try {
      const { data } = await api.post('/playlists', { name: name.trim() })
      setName('')
      toast('Playlist created', 'success')
      await add(data.id)
      await load()
    } catch (err) {
      toast(errMessage(err), 'error')
    } finally {
      setCreating(false)
    }
  }

  if (openId) {
    return (
      <PlaylistDetail
        playlistId={openId}
        onClose={() => setOpenId(null)}
        onDeleted={onClose}
      />
    )
  }

  return (
    <div className="modal modal-open animate-fadein">
      <div className="modal-box glass max-w-md border border-base-content/10">
        <h3 className="font-bold text-lg truncate pr-8">
          Add to playlist
          <div className="text-xs font-normal text-base-content/50 truncate mt-0.5">
            {song.title} {song.artist ? `— ${song.artist}` : ''}
          </div>
        </h3>

        <div className="divider py-1 my-2 opacity-10" />

        <div className="space-y-2 max-h-64 overflow-y-auto no-scrollbar">
          {playlists === null && (
            <div className="flex justify-center py-6">
              <span className="loading loading-dots loading-md text-primary" />
            </div>
          )}
          {playlists?.length === 0 && (
            <p className="text-sm text-base-content/50 py-4 text-center">
              No playlists yet — create your first one below.
            </p>
          )}
          {playlists?.map((pl) => {
            const has = pl.song_ids.includes(song.id)
            return (
              <button
                key={pl.id}
                disabled={has}
                onClick={() => add(pl.id)}
                className={`w-full flex items-center gap-3 p-2.5 rounded-2xl border transition-colors text-left ${
                  has
                    ? 'border-success/30 bg-success/10 cursor-default'
                    : 'border-base-content/5 bg-base-300/50 hover:bg-base-300'
                }`}
              >
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary/40 to-secondary/40 flex items-center justify-center">
                  📃
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold truncate">{pl.name}</div>
                  <div className="text-[10px] text-base-content/40">
                    {pl.song_count} track{pl.song_count === 1 ? '' : 's'}
                    {!pl.is_mine ? ' · public' : ' · yours'}
                  </div>
                </div>
                {has ? (
                  <span className="text-success text-sm">✓</span>
                ) : (
                  <span className="text-base-content/30 text-lg leading-none">+</span>
                )}
              </button>
            )
          })}
        </div>

        <form onSubmit={create} className="flex gap-2 mt-4">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New playlist name…"
            maxLength={60}
            className="input input-sm input-bordered flex-1 bg-base-300/60 border-base-content/10 rounded-xl"
          />
          <button
            disabled={creating || !name.trim()}
            className="btn btn-sm btn-primary rounded-xl px-4"
          >
            {creating ? (
              <span className="loading loading-spinner loading-xs" />
            ) : (
              'Create'
            )}
          </button>
        </form>

        <div className="modal-action">
          <button className="btn btn-sm btn-ghost rounded-xl" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
      <div className="modal-backdrop pointer-events-none" />
    </div>
  )
}
