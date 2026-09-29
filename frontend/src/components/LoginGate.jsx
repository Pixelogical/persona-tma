import React, { useState } from 'react'
import { useApp } from '../store'
import { errMessage } from '../lib/api'
import { displayName } from '../lib/format'
import Avatar from './Avatar'

export default function LoginGate() {
  const { devUsers, loginAs, status } = useApp()
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const quick = async (u) => {
    setBusy(true)
    try {
      await loginAs({ user_id: u.id })
    } catch (e) {
      setError(errMessage(e))
      setBusy(false)
    }
  }

  const create = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    setBusy(true)
    try {
      await loginAs({ first_name: name.trim() })
    } catch (err) {
      setError(errMessage(err))
      setBusy(false)
    }
  }

  if (status === 'error') {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <div className="glass rounded-3xl p-8 text-center max-w-sm w-full">
          <div className="text-4xl mb-3">🚫</div>
          <h1 className="text-xl font-black mb-1">Can't connect</h1>
          <p className="text-sm text-base-content/60">
            Backend is unreachable or Telegram auth failed.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-5">
      <div className="glass rounded-3xl p-7 w-full max-w-sm shadow-glow fade-up">
        <div className="text-center mb-6">
          <div className="mx-auto w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-3xl shadow-glow mb-3">
            🎧
          </div>
          <h1 className="text-2xl font-black hero-title">Persona</h1>
          <p className="text-xs text-base-content/50 mt-1">
            The community chart of the Persona group
          </p>
        </div>

        <p className="text-[11px] uppercase tracking-widest text-base-content/40 font-bold mb-2">
          Browser preview — sign in as
        </p>

        {devUsers.length > 0 && (
          <div className="space-y-2 mb-4 max-h-56 overflow-y-auto no-scrollbar">
            {devUsers.map((u) => (
              <button
                key={u.id}
                disabled={busy}
                onClick={() => quick(u)}
                className="w-full flex items-center gap-3 p-2.5 rounded-2xl bg-base-300/50 hover:bg-base-300 border border-base-content/5 transition-colors"
              >
                <Avatar user={u} size={9} />
                <div className="text-left min-w-0 flex-1">
                  <div className="text-sm font-bold truncate">{displayName(u)}</div>
                  <div className="text-[10px] text-base-content/40">
                    {u.points} points
                  </div>
                </div>
                <span className="text-base-content/30">→</span>
              </button>
            ))}
          </div>
        )}

        <form onSubmit={create} className="flex gap-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="New player name…"
            maxLength={40}
            className="input input-sm input-bordered flex-1 bg-base-300/60 border-base-content/10 rounded-xl"
          />
          <button
            disabled={busy || !name.trim()}
            className="btn btn-sm btn-primary rounded-xl px-4"
          >
            {busy ? <span className="loading loading-spinner loading-xs" /> : 'Join'}
          </button>
        </form>
        {error && <p className="text-error text-xs mt-2">{error}</p>}
        <p className="text-[10px] text-base-content/30 mt-4 text-center">
          Inside Telegram you are signed in automatically
        </p>
      </div>
    </div>
  )
}
