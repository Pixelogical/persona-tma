import React, { useEffect, useState } from 'react'
import api, { errMessage } from '../lib/api'
import { handleNeedStart } from '../lib/play'
import { useApp } from '../store'
import { displayName, formatDuration } from '../lib/format'
import Avatar from './Avatar'
import { StarsDisplay } from './StarRating'

export default function PlaylistDetail({ playlistId, onClose, onDeleted }) {
  const { toast, refreshAll, me } = useApp()
  const [playlist, setPlaylist] = useState(null)
  const [playing, setPlaying] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = () =>
    api
      .get(`/playlists/${playlistId}`)
      .then((r) => setPlaylist(r.data))
      .catch((e) => {
        toast(errMessage(e), 'error')
        onClose()
      })

  useEffect(() => {
    load()
  }, [playlistId])

  const remove = async (songId) => {
    try {
      const { data } = await api.delete(`/playlists/${playlistId}/songs/${songId}`)
      setPlaylist(data)
      refreshAll()
    } catch (e) {
      toast(errMessage(e), 'error')
    }
  }

  const play = async () => {
    if (!playlist?.songs.length) {
      toast('Playlist is empty', 'warning')
      return
    }
    setPlaying(true)
    try {
      const { data } = await api.post(`/playlists/${playlistId}/play`)
      toast(
        `📩 “${data.playlist}” — ${data.started} track(s) sent to your chat with the bot`,
        'success'
      )
    } catch (e) {
      if (!handleNeedStart(e, toast)) toast(errMessage(e), 'error')
    } finally {
      setPlaying(false)
    }
  }

  const removePlaylist = async () => {
    try {
      await api.delete(`/playlists/${playlistId}`)
      toast('Playlist deleted', 'success')
      refreshAll()
      onDeleted ? onDeleted() : onClose()
    } catch (e) {
      toast(errMessage(e), 'error')
    }
  }

  return (
    <div className="modal modal-open">
      <div className="modal-box glass max-w-lg max-h-[85vh] border border-base-content/10 flex flex-col">
        {playlist ? (
          <>
            <div className="flex items-start gap-3 pr-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-2xl shadow-glow shrink-0">
                🎶
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-black text-lg leading-tight truncate">
                  {playlist.name}
                </h3>
                <div className="flex items-center gap-2 mt-1.5">
                  <Avatar user={playlist.owner} size={6} />
                  <span className="text-[11px] text-base-content/50">
                    {displayName(playlist.owner)} · {playlist.song_count} track
                    {playlist.song_count === 1 ? '' : 's'} · public
                  </span>
                </div>
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={play}
                disabled={playing || !playlist.song_count}
                className="btn btn-primary btn-sm flex-1 rounded-xl font-bold gap-2"
              >
                {playing ? (
                  <span className="loading loading-spinner loading-xs" />
                ) : (
                  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
                Play in my chat
              </button>
              {playlist.is_mine && (
                <button
                  onClick={() => (confirmDelete ? removePlaylist() : setConfirmDelete(true))}
                  className={`btn btn-sm rounded-xl ${
                    confirmDelete ? 'btn-error' : 'btn-ghost text-error'
                  }`}
                >
                  {confirmDelete ? 'Sure?' : 'Delete'}
                </button>
              )}
            </div>

            <div className="divider py-1 my-3 opacity-10" />

            <div className="overflow-y-auto flex-1 space-y-2 pr-1">
              {playlist.songs.length === 0 && (
                <p className="text-sm text-base-content/50 text-center py-8">
                  No tracks yet — add songs from the chart.
                </p>
              )}
              {playlist.songs.map((ps, index) => (
                <div
                  key={ps.song.id}
                  className="flex items-center gap-3 p-2 rounded-xl bg-base-300/40 border border-base-content/5"
                >
                  <span className="w-5 text-center text-xs font-black text-base-content/30">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-bold truncate">{ps.song.title}</div>
                    <div className="flex items-center gap-2 text-[10px] text-base-content/45 min-w-0">
                      <span className="truncate">
                        {ps.song.artist || 'Unknown artist'}
                      </span>
                      <StarsDisplay value={ps.song.avg} size={9} />
                      {formatDuration(ps.song.duration) && (
                        <span>{formatDuration(ps.song.duration)}</span>
                      )}
                    </div>
                  </div>
                  {playlist.is_mine && (
                    <button
                      className="btn btn-xs btn-circle btn-ghost text-error/70"
                      onClick={() => remove(ps.song.id)}
                      title="Remove"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>

            <div className="modal-action mt-3">
              <button className="btn btn-sm btn-ghost rounded-xl" onClick={onClose}>
                Close
              </button>
            </div>
          </>
        ) : (
          <div className="flex justify-center py-14">
            <span className="loading loading-dots loading-md text-primary" />
          </div>
        )}
      </div>
      <div className="modal-backdrop pointer-events-none" onClick={onClose} />
    </div>
  )
}
