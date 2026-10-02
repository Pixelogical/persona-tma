import React, { useState } from 'react'
import { useApp } from './store'
import ChartView from './views/ChartView'
import LoginGate from './components/LoginGate'
import PlaylistsView from './views/PlaylistsView'
import ProfileView from './views/ProfileView'
import ProfileModal from './components/ProfileModal'
import Toasts from './components/Toasts'
import Avatar from './components/Avatar'
import { displayName } from './lib/format'
import { haptic } from './lib/telegram'

const NAV = [
  {
    id: 'chart',
    label: 'Chart',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M4 20V10M10 20V4M16 20v-8M22 20H2" transform="scale(0.9) translate(1,1)" />
      </svg>
    ),
  },
  {
    id: 'playlists',
    label: 'Playlists',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15V6m0 0-9.5 3.5-5-2L2 6.5v11.6L6.5 21l5-2L21 15zM6.5 8v6.5" />
        <path d="M17 8l4-1.5" />
      </svg>
    ),
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5" />
      </svg>
    ),
  },
]

function Header({ view, setView }) {
  const { me } = useApp()
  return (
    <header className="sticky top-0 z-30 glass border-b border-base-content/5">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-lg shadow-glow">
            🎧
          </div>
          <div>
            <div className="text-lg font-black leading-none hero-title">
              Persona
            </div>
            <div className="text-[9px] uppercase tracking-[0.2em] text-base-content/40 font-bold mt-0.5">
              group music chart
            </div>
          </div>
        </div>
        {me && (
          <button
            onClick={() => {
              haptic('light')
              setView('profile')
            }}
            className="flex items-center gap-2"
            title={displayName(me)}
          >
            <div className="text-right hidden min-[380px]:block">
              <div className="text-[11px] font-bold max-w-[90px] truncate leading-tight">
                {displayName(me)}
              </div>
              <div className="text-[9px] text-warning font-extrabold">
                {me.points} pts
              </div>
            </div>
            <Avatar user={me} size={10} />
          </button>
        )}
      </div>
    </header>
  )
}

export default function App() {
  const { status, toasts, profileUserId, closeProfile } = useApp()
  const [view, setView] = useState('chart')

  return (
    <div className="min-h-screen">
      <Toasts toasts={toasts} />

      {status === 'loading' ? (
        <div className="min-h-screen flex flex-col items-center justify-center gap-4">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-3xl shadow-glow animate-pulse">
            🎧
          </div>
          <div className="text-xl font-black hero-title">Persona</div>
          <span className="loading loading-dots loading-sm text-primary" />
        </div>
      ) : status === 'ready' ? (
        <>
          <Header view={view} setView={setView} />

          <main className="pt-4">
            {view === 'chart' && <ChartView />}
            {view === 'playlists' && <PlaylistsView />}
            {view === 'profile' && <ProfileView />}
          </main>

          <footer className="text-center pb-28 -mt-16 text-[11px] text-base-content/30 font-medium">
            Persona Assistant v1.1 beta • Created with <span className="text-primary">❤</span> by Pixel
          </footer>

          <div className="fixed bottom-0 inset-x-0 z-40 mx-auto max-w-[640px] pb-[max(env(safe-area-inset-bottom),12px)] px-6">
            <div className="glass rounded-3xl px-2 py-1.5 flex justify-around shadow-card border border-base-content/10">
              {NAV.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    haptic('light')
                    setView(item.id)
                  }}
                  className={`flex flex-col items-center gap-0.5 px-5 py-1.5 rounded-2xl transition-all text-[10px] font-bold ${
                    view === item.id
                      ? 'text-primary bg-primary/10'
                      : 'text-base-content/40'
                  }`}
                >
                  {item.icon}
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {profileUserId && (
            <ProfileModal userId={profileUserId} onClose={closeProfile} />
          )}
        </>
      ) : (
        <LoginGate />
      )}
    </div>
  )
}
