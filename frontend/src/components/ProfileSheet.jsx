import React, { useCallback, useEffect, useRef, useState } from 'react'
import api, { errMessage } from '../lib/api'
import { useApp } from '../store'
import { haptic } from '../lib/telegram'
import { displayName, timeAgo } from '../lib/format'
import { ENNEA_TYPES, MBTI_TYPES, SOCIONICS_TYPES } from '../lib/profileTypes'
import Avatar from './Avatar'
import { StarsDisplay } from './StarRating'

const DEFAULTS = new Set(['XXXX', 'XwX', 'XXX'])

function TypeBadge({ label, value }) {
  const unset = !value || DEFAULTS.has(value)
  return (
    <div
      className={`px-2.5 py-1 rounded-xl border text-center ${
        unset
          ? 'border-base-content/10 bg-base-300/40 text-base-content/30'
          : 'border-primary/30 bg-primary/10 text-primary'
      }`}
    >
      <div className="text-[8px] uppercase tracking-wider font-bold opacity-70">
        {label}
      </div>
      <div className="text-[11px] font-black leading-tight">{value}</div>
    </div>
  )
}

function RecentSongs({ songs }) {
  if (!songs || songs.length === 0) return null
  return (
    <section>
      <h3 className="text-sm font-bold tracking-wide text-base-content/70 uppercase mb-2">
        Recent songs sent
      </h3>
      <div className="space-y-2">
        {songs.map((s) => (
          <div key={s.id} className="glass rounded-2xl p-2.5 flex items-center gap-3">
            {s.cover ? (
              <img
                src={s.cover}
                alt=""
                loading="lazy"
                referrerPolicy="no-referrer"
                className="w-9 h-9 rounded-lg object-cover border border-base-content/10 shrink-0"
              />
            ) : (
              <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary/40 to-secondary/30 flex items-center justify-center text-sm shrink-0">
                🎵
              </div>
            )}
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold truncate">{s.title}</div>
              <div className="text-[10px] text-base-content/45 truncate">
                {s.artist || 'Unknown artist'} · {timeAgo(s.created_at)}
              </div>
            </div>
            <div className="shrink-0 flex flex-col items-end">
              <span className="text-[11px] font-extrabold text-warning">
                {s.avg ? s.avg.toFixed(1) : '—'}
              </span>
              <StarsDisplay value={s.avg} size={9} />
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

function Comments({ userId }) {
  const { me, toast, openProfile } = useApp()
  const [comments, setComments] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(
    () =>
      api
        .get(`/users/${userId}/comments`)
        .then((r) => setComments(r.data))
        .catch(() => setComments([])),
    [userId]
  )
  useEffect(() => {
    setComments(null)
    load()
  }, [load])

  const submit = async (e) => {
    e.preventDefault()
    if (!text.trim() || busy) return
    setBusy(true)
    try {
      const { data } = await api.post(`/users/${userId}/comments`, {
        text: text.trim(),
      })
      setComments((c) => [data, ...(c || [])])
      setText('')
      haptic('success')
    } catch (err) {
      toast(errMessage(err), 'error')
    } finally {
      setBusy(false)
    }
  }

  const remove = async (id) => {
    try {
      await api.delete(`/comments/${id}`)
      setComments((c) => c.filter((x) => x.id !== id))
    } catch (err) {
      toast(errMessage(err), 'error')
    }
  }

  return (
    <section>
      <h3 className="text-sm font-bold tracking-wide text-base-content/70 uppercase mb-2">
        Comments{' '}
        <span className="text-[10px] text-base-content/40 normal-case">
          {comments ? `(${comments.length})` : ''}
        </span>
      </h3>

      <form onSubmit={submit} className="flex gap-2 mb-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Leave a comment…"
          maxLength={280}
          className="input input-sm input-bordered flex-1 bg-base-300/60 border-base-content/10 rounded-xl"
        />
        <button
          disabled={busy || !text.trim()}
          className="btn btn-sm btn-primary rounded-xl px-4"
        >
          {busy ? <span className="loading loading-spinner loading-xs" /> : 'Post'}
        </button>
      </form>

      {comments === null ? (
        <div className="flex justify-center py-4">
          <span className="loading loading-dots loading-sm text-primary" />
        </div>
      ) : comments.length === 0 ? (
        <p className="text-xs text-base-content/40 text-center py-3">
          No comments yet — be the first!
        </p>
      ) : (
        <div className="space-y-2">
          {comments.map((c) => (
            <div key={c.id} className="glass rounded-2xl p-3 flex gap-2.5">
              <button onClick={() => c.author.id !== me?.id && openProfile(c.author.id)}>
                <Avatar user={c.author} size={7} />
              </button>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-bold truncate">
                    {displayName(c.author)}
                  </span>
                  <span className="text-[9px] text-base-content/35">
                    {timeAgo(c.created_at)}
                  </span>
                  {c.can_delete && (
                    <button
                      className="ml-auto text-base-content/30 hover:text-error text-xs px-1"
                      title="Delete comment"
                      onClick={() => remove(c.id)}
                    >
                      ✕
                    </button>
                  )}
                </div>
                <div className="text-xs text-base-content/80 mt-0.5 break-words">
                  {c.text}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default function ProfileSheet({ userId, rev }) {
  const { me, toast, refreshMe, refreshAll } = useApp()
  const [profile, setProfile] = useState(null)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ bio: '', mbti: 'XXXX', enneagram: 'XwX', socionics: 'XXX' })
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/users/${userId}/profile`)
      .then((r) => {
        if (cancelled) return
        setProfile(r.data)
        setForm({
          bio: r.data.user.bio || '',
          mbti: r.data.user.mbti || 'XXXX',
          enneagram: r.data.user.enneagram || 'XwX',
          socionics: r.data.user.socionics || 'XXX',
        })
      })
      .catch(() => !cancelled && setProfile(null))
    return () => {
      cancelled = true
    }
  }, [userId, rev])

  if (!profile) {
    return (
      <div className="flex justify-center py-16">
        <span className="loading loading-bars loading-md text-primary" />
      </div>
    )
  }

  const { user } = profile

  const save = async (e) => {
    e.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      try {
        await api.post('/me/profile', form, { timeout: 12000 })
      } catch (err) {
        // A real API error (401/422/…) has a response — show it.
        if (err.response) throw err
        // Timeouts / dropped responses (proxy, cloudflared): the write
        // itself still lands — never hang on a reply that never arrives,
        // confirm through the regular profile GET instead.
      }
      const { data } = await api.get(`/users/${userId}/profile`)
      setProfile(data)
      setEditing(false)
      toast('✅ Profile saved', 'success')
      haptic('success')
      refreshMe()
    } catch (err) {
      toast(errMessage(err), 'error')
      haptic('error')
    } finally {
      setSaving(false)
    }
  }

  const pickAvatar = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || uploading) return
    if (file.size > 2 * 1024 * 1024) {
      toast('Image too large (max 2 MB)', 'error')
      return
    }
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const { data } = await api.post('/me/avatar', fd, { timeout: 30000 })
      setProfile((p) => ({ ...p, user: data }))
      toast('🖼️ Profile picture updated', 'success')
      refreshMe()
      refreshAll()
    } catch (err) {
      if (err.response) {
        toast(errMessage(err, 'Upload failed'), 'error')
        haptic('error')
      } else {
        // response lost in transit — verify the new picture via /me
        await refreshMe()
        refreshAll()
        toast('🖼️ Profile picture updated', 'success')
      }
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="space-y-5">
      {/* identity */}
      <div className="glass rounded-3xl p-6 shadow-card text-center relative overflow-hidden">
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-primary/20 to-transparent pointer-events-none" />
        <div className="relative">
          <div className="flex justify-center">
            <div className="relative">
              <Avatar user={user} size={22} ring />
              {profile.is_me && (
                <button
                  onClick={() => fileRef.current?.click()}
                  disabled={uploading}
                  title="Change profile picture"
                  className="absolute -bottom-1 -right-1 w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center shadow-glow border-2 border-base-100"
                >
                  {uploading ? (
                    <span className="loading loading-spinner loading-xs" />
                  ) : (
                    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                      <circle cx="12" cy="13" r="4" />
                    </svg>
                  )}
                </button>
              )}
              <input
                ref={fileRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={pickAvatar}
              />
            </div>
          </div>
          <h2 className="text-xl font-black mt-3">{displayName(user)}</h2>
          {user.username && <p className="text-xs text-base-content/50">@{user.username}</p>}
          {user.bio && (
            <p className="text-xs text-base-content/70 mt-2 break-words">{user.bio}</p>
          )}

          <div className="grid grid-cols-3 gap-2 mt-4">
            <TypeBadge label="MBTI" value={user.mbti} />
            <TypeBadge label="Enneagram" value={user.enneagram} />
            <TypeBadge label="Socionics" value={user.socionics} />
          </div>

          {profile.is_me && !editing && (
            <button
              className="btn btn-xs btn-ghost rounded-xl text-primary mt-3"
              onClick={() => setEditing(true)}
            >
              ✏️ Edit profile
            </button>
          )}

          <div className="grid grid-cols-3 gap-2 mt-5">
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black text-transparent bg-clip-text bg-gradient-to-br from-primary to-secondary">
                {user.points}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Points
              </div>
            </div>
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black">{profile.songs_sent}</div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Songs
              </div>
            </div>
            <div className="bg-base-300/50 rounded-2xl py-3 border border-base-content/5">
              <div className="text-xl font-black text-warning">
                {profile.avg_rating ? profile.avg_rating.toFixed(1) : '—'}
              </div>
              <div className="text-[10px] uppercase tracking-wider text-base-content/40 font-bold">
                Avg · {profile.rated_songs} rated
              </div>
            </div>
          </div>
          <p className="text-[10px] text-base-content/35 mt-3">
            Member since {timeAgo(user.created_at)} · avg rating counts only rated
            songs they sent
          </p>
        </div>
      </div>

      {/* edit form */}
      {editing && (
        <form
          onSubmit={save}
          className="glass rounded-3xl p-4 space-y-3 border border-primary/20"
        >
          <div className="form-control">
            <label className="label py-1">
              <span className="label-text text-[10px] uppercase tracking-wider font-bold text-base-content/50">
                Bio
              </span>
            </label>
            <textarea
              value={form.bio}
              onChange={(e) => setForm({ ...form, bio: e.target.value })}
              maxLength={280}
              rows={3}
              placeholder="Tell the group about yourself…"
              className="textarea textarea-bordered bg-base-300/60 border-base-content/10 rounded-2xl text-sm"
            />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <label className="form-control">
              <span className="label-text text-[10px] uppercase font-bold text-base-content/50 mb-1">
                MBTI
              </span>
              <select
                value={form.mbti}
                onChange={(e) => setForm({ ...form, mbti: e.target.value })}
                className="select select-sm select-bordered bg-base-300/60 border-base-content/10 rounded-xl font-bold"
              >
                <option value="XXXX">XXXX</option>
                {MBTI_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="form-control">
              <span className="label-text text-[10px] uppercase font-bold text-base-content/50 mb-1">
                Enneagram
              </span>
              <select
                value={form.enneagram}
                onChange={(e) => setForm({ ...form, enneagram: e.target.value })}
                className="select select-sm select-bordered bg-base-300/60 border-base-content/10 rounded-xl font-bold"
              >
                <option value="XwX">XwX</option>
                {ENNEA_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="form-control">
              <span className="label-text text-[10px] uppercase font-bold text-base-content/50 mb-1">
                Socionics
              </span>
              <select
                value={form.socionics}
                onChange={(e) => setForm({ ...form, socionics: e.target.value })}
                className="select select-sm select-bordered bg-base-300/60 border-base-content/10 rounded-xl font-bold"
              >
                <option value="XXX">XXX</option>
                {SOCIONICS_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              className="btn btn-sm btn-ghost rounded-xl"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn btn-sm btn-primary rounded-xl px-5"
            >
              {saving ? <span className="loading loading-spinner loading-xs" /> : 'Save'}
            </button>
          </div>
        </form>
      )}

      <RecentSongs songs={profile.top_songs} />
      <Comments userId={user.id} />
    </div>
  )
}
