import { errMessage } from './api'
import { openLink } from './telegram'

/**
 * If a play request failed because the user never opened a DM with the bot,
 * redirect them to the bot chat (Telegram deep link with `?start=play_<id>`).
 * Once they press Start, the bot streams the playlist automatically.
 * Returns true when the error was handled this way.
 */
export function handleNeedStart(e, toast) {
  const detail = e?.response?.data?.detail
  if (!detail || typeof detail !== 'object' || !detail.need_start) return false
  if (detail.start_link) {
    openLink(detail.start_link)
    toast(
      'Press START in the bot chat — your playlist begins there instantly 🎧',
      'warning'
    )
  } else {
    toast(errMessage(e), 'error')
  }
  return true
}
