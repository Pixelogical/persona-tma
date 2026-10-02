import React from 'react'
import { tmaDiag } from '../lib/telegram'

/**
 * Not a login screen — there is no manual login anymore. Users are signed
 * in permanently and automatically with the Telegram account that opened
 * the Mini App. This card only appears when the app is opened somewhere it
 * can't identify you (a normal browser without a session).
 */
export default function LoginGate() {
  const d = tmaDiag()
  return (
    <div className="min-h-screen flex items-center justify-center p-5">
      <div className="glass rounded-3xl p-8 text-center max-w-sm w-full fade-up">
        <div className="mx-auto w-16 h-16 rounded-3xl bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-3xl shadow-glow mb-4">
          🎧
        </div>
        <h1 className="text-xl font-black hero-title mb-2">Persona</h1>
        <p className="text-sm text-base-content/60 leading-relaxed">
          Persona signs you in automatically with your
          <span className="font-bold text-base-content"> Telegram account</span>.
        </p>
        <div className="divider my-4 opacity-10" />
        <p className="text-xs text-base-content/50">
          Open this app <span className="font-bold">inside Telegram</span> — from
          the Persona group via the 🎧 menu button — and you&apos;ll be in
          instantly.
        </p>
        <p
          className="mt-6 text-[9px] font-mono text-base-content/25 select-all break-all"
          title="sign-in diagnostics"
        >
          {`tg=${d.sdk ? 1 : 0} id=${d.initDataLen} url=${d.urlData ? 1 : 0} pf=${d.platform} v=${d.version} @ ${d.host}`}
        </p>
      </div>
    </div>
  )
}
