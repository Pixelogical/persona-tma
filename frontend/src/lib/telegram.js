// Resolve the Telegram WebApp object lazily at CALL time (not module-load
// time) so we never miss it if telegram-web-app.js executes slightly later.
const getTg = () =>
  typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

// Fallback for clients that pass WebApp data via the launch URL but where
// telegram.org/js/telegram-web-app.js failed to load (the SDK host is
// unreachable/blocked on some networks — a common case on desktop).
function webappFromUrl() {
  if (typeof window === 'undefined') return null
  const q = new URLSearchParams(window.location.search)
  if (!q.has('initData') && !q.has('auth_date') && !q.has('user')) return null
  const raw = q.get('initData') || ''
  const pairs = new URLSearchParams(raw || window.location.search.slice(1))
  let user = null
  try {
    let u = pairs.get('user')
    if (typeof u === 'string') {
      try {
        u = decodeURIComponent(u)
      } catch {
        /* already decoded */
      }
      user = JSON.parse(u)
    }
  } catch {
    user = null
  }
  return { initData: raw, user }
}

export function isTMA() {
  const t = getTg()
  if (t) {
    // initData is non-empty only when opened inside a real Telegram client.
    if (
      (typeof t.initData === 'string' && t.initData.length > 0) ||
      (typeof t.initDataRaw === 'string' && t.initDataRaw.length > 0) ||
      !!t.initDataUnsafe?.user
    ) {
      return true
    }
  }
  return !!webappFromUrl()
}

export function tgInitData() {
  const t = getTg()
  // Telegram Desktop sometimes fills initDataRaw while initData is empty —
  // send whichever the client provided.
  const fromSdk = t?.initData || t?.initDataRaw || ''
  if (fromSdk) return fromSdk
  return webappFromUrl()?.initData || ''
}

// Small fingerprint of the sign-in environment, shown on the error screen —
// enough to tell "not in Telegram" from "SDK blocked" from "bad signature".
export function tmaDiag() {
  const t = getTg()
  const fromUrl = webappFromUrl()
  return {
    sdk: !!t,
    initDataLen: (t?.initData || t?.initDataRaw || '').length,
    urlData: !!fromUrl,
    platform: t?.platform || '-',
    version: t?.version || '-',
    host: typeof location !== 'undefined' ? location.host : '-',
  }
}

export function getTelegramUser() {
  return getTg()?.initDataUnsafe?.user || null
}

let bootstrapped = false

export function initTelegram(onReady) {
  const run = () => {
    if (bootstrapped) return
    bootstrapped = true
    onReady?.()
  }
  const tg = getTg()
  if (tg) {
    try {
      tg.ready()
      tg.expand()
      tg.setHeaderColor?.('#090a0f')
      tg.setBackgroundColor?.('#090a0f')
      tg.setHeaderTextColor?.('#f3f1f2')
      tg.applyThemeParams?.({
        bg_color: '#090a0f',
        secondary_bg_color: '#11131a',
      })
    } catch {
      /* running outside Telegram */
    }
  }
  // The official SDK fires `ttminit` when it finishes collecting init data
  // (it reads it from the URL / native bridge itself — this is the path that
  // works on Desktop when telegram.org's script loaded slowly or late).
  document.addEventListener('ttminit', run, { once: true })
  document.addEventListener('ttmready', run, { once: true })
  window.addEventListener('TelegramWebAppReady', run, { once: true })
  // Some desktop clients inject window.Telegram.WebApp a moment later.
  let waits = 0
  const timer = setInterval(() => {
    if (getTg() || ++waits > 15) clearInterval(timer)
    if (getTg()) run()
  }, 200)
  // The URL fallback is available immediately — no need to wait for anything.
  if (webappFromUrl()) run()
}

export function haptic(kind = 'light') {
  const tg = getTg()
  try {
    if (kind === 'success') tg?.HapticFeedback?.notificationOccurred('success')
    else if (kind === 'error') tg?.HapticFeedback?.notificationOccurred('error')
    else tg?.HapticFeedback?.impactOccurred(kind)
  } catch {
    /* noop */
  }
}

export function openLink(url) {
  if (!url) return
  const tg = getTg()
  if (tg?.openTelegramLink) {
    try {
      const res = tg.openTelegramLink(url)
      if (res !== false) return
    } catch {
      /* fall through */
    }
  }
  window.open(url, '_blank', 'noopener')
}

export function backButton(onClick) {
  const btn = getTg()?.BackButton
  if (!btn) return () => {}
  btn.onClick(onClick)
  btn.show()
  return () => {
    try {
      btn.hide()
      btn.offClick(onClick)
    } catch {
      /* noop */
    }
  }
}
