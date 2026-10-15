import React, { useState } from 'react'
import api, { errMessage } from '../lib/api'
import { haptic } from '../lib/telegram'
import { handleNeedStart } from '../lib/play'
import Portal from './Portal'
import { useApp } from '../store'

function Stepper({ label, min, max, step, value, onChange, format }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-base-content/80">{label}</span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          className="btn btn-sm btn-circle btn-ghost border border-base-content/10"
          disabled={value <= min}
          onClick={() => {
            haptic('light')
            onChange(Math.max(min, value - step))
          }}
        >
          −
        </button>
        <span className="w-16 text-center text-sm font-extrabold tabular-nums">
          {format(value)}
        </span>
        <button
          type="button"
          className="btn btn-sm btn-circle btn-ghost border border-base-content/10"
          disabled={value >= max}
          onClick={() => {
            haptic('light')
            onChange(Math.min(max, value + step))
          }}
        >
          +
        </button>
      </div>
    </div>
  )
}

export default function TopsModal({ onClose }) {
  const { toast } = useApp()
  const [avgTenths, setAvgTenths] = useState(40) // 0.1-star steps
  const [minVotes, setMinVotes] = useState(3)
  const [maxTracks, setMaxTracks] = useState(50)
  const [shuffle, setShuffle] = useState(false)
  const [busy, setBusy] = useState(false)

  const play = async () => {
    if (busy) return
    setBusy(true)
    haptic('medium')
    try {
      const { data } = await api.post('/playlists/tops/play', {
        min_avg: avgTenths / 10,
        min_votes: minVotes,
        max_tracks: maxTracks,
        shuffle,
      })
      toast(
        `📩 “${data.playlist}” — ${data.started} track(s) on the way to your bot chat`,
        'success'
      )
      onClose()
    } catch (e) {
      if (!handleNeedStart(e, toast)) toast(errMessage(e), 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Portal>
    <div className="modal modal-open animate-fadein">
      <div className="modal-box glass max-w-sm border border-base-content/10">
        <h3 className="font-bold text-lg truncate pr-8">
          🏆 Tops of Persona
          <div className="text-xs font-normal text-base-content/50 truncate mt-0.5">
            The chart&apos;s best — filtered live by you
          </div>
        </h3>

        <div className="divider py-1 my-2 opacity-10" />

        <div className="divide-y divide-base-content/5">
          <Stepper
            label="Min average stars"
            min={10}
            max={50}
            step={1}
            value={avgTenths}
            onChange={setAvgTenths}
            format={(v) => `${(v / 10).toFixed(1)} ★`}
          />
          <Stepper
            label="Min voters"
            min={1}
            max={20}
            step={1}
            value={minVotes}
            onChange={setMinVotes}
            format={(v) => `${v}`}
          />
          <Stepper
            label="Max tracks"
            min={5}
            max={50}
            step={5}
            value={maxTracks}
            onChange={setMaxTracks}
            format={(v) => `${v}`}
          />
          <label className="flex items-center justify-between py-2.5 cursor-pointer">
            <span className="text-sm text-base-content/80">🔀 Shuffle order</span>
            <input
              type="checkbox"
              className="toggle toggle-primary toggle-sm"
              checked={shuffle}
              onChange={(e) => setShuffle(e.target.checked)}
            />
          </label>
        </div>

        <button
          onClick={play}
          disabled={busy}
          className="btn btn-sm w-full mt-4 rounded-xl bg-gradient-to-r from-primary to-secondary border-0 text-white font-bold gap-2 shadow-glow"
        >
          {busy ? (
            <span className="loading loading-spinner loading-xs" />
          ) : (
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
          Play in my chat
        </button>

        <div className="modal-action">
          <button className="btn btn-sm btn-ghost rounded-xl" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
      <div className="modal-backdrop pointer-events-none" />
    </div>
    </Portal>
  )
}
