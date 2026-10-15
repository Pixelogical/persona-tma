import React, { useState } from 'react'
import api, { errMessage } from '../lib/api'
import { useApp } from '../store'
import { haptic } from '../lib/telegram'

export default function SongTags({ song, tags, onTags, onClose }) {
  const { toast } = useApp()
  const [value, setValue] = useState('')
  const [busy, setBusy] = useState(false)

  const add = async (e) => {
    e.preventDefault()
    const tag = value.trim().replace(/^#+/, '')
    if (!tag || busy) return
    setBusy(true)
    try {
      const { data } = await api.post(`/songs/${song.id}/tags`, { tag })
      onTags(data.tags)
      setValue('')
      toast(`#${data.tags[data.tags.length - 1]} added`, 'success')
      haptic('success')
    } catch (err) {
      toast(errMessage(err), 'error')
      haptic('error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal modal-open animate-fadein">
      <div className="modal-box glass max-w-md border border-base-content/10">
        <h3 className="font-bold text-lg truncate pr-8">
          Tags
          <div className="text-xs font-normal text-base-content/50 truncate mt-0.5">
            {song.title} {song.artist ? `— ${song.artist}` : ''}
          </div>
        </h3>

        <div className="divider py-1 my-2 opacity-10" />

        {tags.length === 0 ? (
          <p className="text-sm text-base-content/50 py-4 text-center">
            No tags yet — add the first genre below, or reply to the song in
            the group with <span className="font-bold">#pop</span>-style
            hashtags.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((t) => (
              <span
                key={t}
                className="badge badge-lg rounded-xl border border-secondary/30 bg-secondary/10 text-secondary font-bold"
              >
                #{t}
              </span>
            ))}
          </div>
        )}

        <form onSubmit={add} className="flex gap-2 mt-4">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="#pop, indie_rock…"
            maxLength={40}
            dir="ltr"
            className="input input-sm input-bordered flex-1 bg-base-300/60 border-base-content/10 rounded-xl"
          />
          <button
            disabled={busy || !value.trim().replace(/^#+/, '')}
            className="btn btn-sm btn-primary rounded-xl px-4"
          >
            {busy ? (
              <span className="loading loading-spinner loading-xs" />
            ) : (
              '# Add'
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
