import React, { useState } from 'react'
import { useApp } from '../store'
import { displayName, formatCount, formatDuration, timeAgo } from '../lib/format'
import { haptic } from '../lib/telegram'
import Avatar from './Avatar'
import StarRating, { StarsDisplay } from './StarRating'

function Cover({ song }) {
  const [broken, setBroken] = useState(false)
  if (song.cover && !broken) {
    return (
      <img
        src={song.cover}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setBroken(true)}
        className="w-11 h-11 rounded-xl object-cover border border-base-content/10 shrink-0"
      />
    )
  }
  return (
    <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary/40 to-secondary/30 border border-base-content/10 flex items-center justify-center text-base shrink-0">
      🎵
    </div>
  )
}

export default function SongCard({
  song,
  rank,
  isTop3,
  onVote,
  onAdd,
  onPin,
  busy = false,
}) {
  const { openProfile } = useApp()
  const [localStars, setLocalStars] = useState(song.my_vote || 0)
  const [voting, setVoting] = useState(false)

  const vote = async (stars) => {
    if (voting) return
    setVoting(true)
    const prev = localStars
    setLocalStars(stars)
    try {
      await onVote(song, stars)
      haptic('success')
    } catch (e) {
      setLocalStars(prev)
      haptic('error')
    } finally {
      setVoting(false)
    }
  }

  const top3 = rank <= 3

  return (
    <div
      className={`glass rounded-2xl p-3.5 shadow-card transition-transform active:scale-[0.99] ${
        busy ? 'opacity-50 pointer-events-none' : ''
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`w-8 shrink-0 text-center font-black ${
            top3 ? 'text-transparent bg-clip-text bg-gradient-to-b from-warning to-secondary text-lg' : 'text-base-content/30 text-base'
          }`}
        >
          {top3 ? ['🥇', '🥈', '🥉'][rank - 1] : `#${rank}`}
        </div>

        <Cover song={song} />

        <div className="min-w-0 flex-1">
          <div className="font-bold text-[15px] leading-tight truncate">
            {song.title}
          </div>
          <div className="text-xs text-base-content/50 truncate mt-0.5">
            {song.artist || 'Unknown artist'}
            {formatDuration(song.duration) ? ` · ${formatDuration(song.duration)}` : ''}
          </div>
          <div className="flex items-center gap-1.5 mt-1.5">
            <button
              className="flex items-center gap-1.5 min-w-0 rounded-lg hover:bg-base-content/5 px-1 -mx-1"
              title="View sender's profile"
              onClick={(e) => {
                e.stopPropagation()
                haptic('light')
                openProfile(song.sender.id)
              }}
            >
              <Avatar user={song.sender} size={5} />
              <span className="text-[10px] text-base-content/45 truncate max-w-[110px]">
                {displayName(song.sender)}
              </span>
            </button>
            <span className="text-[9px] text-base-content/30">·</span>
            <span className="text-[10px] text-base-content/40">
              {timeAgo(song.created_at)}
            </span>
            {formatCount(song.listeners) && (
              <>
                <span className="text-[9px] text-base-content/30">·</span>
                <span
                  className="text-[10px] text-secondary font-semibold whitespace-nowrap"
                  title="Global listeners on last.fm"
                >
                  🌐 {formatCount(song.listeners)} global listeners
                </span>
              </>
            )}
          </div>
        </div>

        <div className="shrink-0 flex flex-col items-end gap-1">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-extrabold text-warning">
              {song.avg ? song.avg.toFixed(1) : '—'}
            </span>
            <StarsDisplay value={song.avg} size={11} />
          </div>
          <span className="text-[10px] text-base-content/40">
            {song.votes} vote{song.votes === 1 ? '' : 's'}
          </span>
        </div>
      </div>

      <div className="divider my-2.5 py-0 opacity-10" />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StarRating value={localStars} onVote={vote} disabled={voting} />
          {localStars > 0 && (
            <span className="text-[9px] uppercase tracking-wider text-primary font-bold">
              yours
            </span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          <button
            className="btn btn-xs btn-circle btn-ghost text-primary"
            title="Add to playlist"
            onClick={(e) => {
              e.stopPropagation()
              haptic('light')
              onAdd(song)
            }}
          >
            <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
          {isTop3 && (
            <button
              className="btn btn-xs btn-circle btn-ghost text-warning"
              title="Pin this song (top voters only)"
              onClick={(e) => {
                e.stopPropagation()
                haptic('medium')
                onPin(song)
              }}
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 17v5M9 3h6l1 7 2 2H4l2-2 1-7z" />
              </svg>
            </button>
          )}
          {song.link && (
            <a
              className="btn btn-xs btn-circle btn-ghost text-base-content/50"
              title="Open in Telegram"
              href={song.link}
              target="_blank"
              rel="noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              ↗
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
