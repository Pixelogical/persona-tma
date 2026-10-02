// Resolve the Telegram WebApp object lazily at CALL time (not module-load
// time) so we never miss it if telegram-web-app.js executes slightly later.
const getTg = () =>
  typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export function isTMA() {
  const t = getTg()
  if (!t) return false
  // initData is non-empty only when opened inside a real Telegram client.
  return (
    (typeof t.initData === 'string' && t.initData.length > 0) ||
    !!t.initDataUnsafe?.user
  )
}

export function tgInitData() {
  const t = getTg()
  // Telegram Desktop sometimes fills initDataRaw while initData is empty —
  // send whichever the client provided.
  return t?.initData || t?.initDataRaw || ''
}

export function getTelegramUser() {
  return getTg()?.initDataUnsafe?.user || null
}

export function initTelegram() {
  const tg = getTg()
  if (!tg) return
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
