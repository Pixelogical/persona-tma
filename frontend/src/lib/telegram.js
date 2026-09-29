const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export function isTMA() {
  return !!(tg && tg.initData && tg.initData.length > 0)
}

export function tgInitData() {
  return tg?.initData || ''
}

export function initTelegram() {
  if (!tg) return
  try {
    tg.ready()
    tg.expand()
    tg.setHeaderColor?.('#0b0f1a')
    tg.setBackgroundColor?.('#0b0f1a')
    tg.setHeaderTextColor?.('#e8ebf4')
    tg.applyThemeParams?.({
      bg_color: '#0b0f1a',
      secondary_bg_color: '#0b0f1a',
    })
  } catch {
    /* running outside Telegram */
  }
}

export function haptic(kind = 'light') {
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
  const btn = tg?.BackButton
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
