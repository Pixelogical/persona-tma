export function displayName(user) {
  if (!user) return 'Unknown'
  const name = [user.first_name, user.last_name].filter(Boolean).join(' ')
  return name || user.username || `user${user.id}`
}

export function initials(user) {
  const name = displayName(user).trim()
  const parts = name.split(/\s+/).filter(Boolean)
  if (parts.length >= 2)
    return (parts[0][0] + parts[1][0]).toUpperCase()
  return (parts[0]?.[0] || '?').toUpperCase()
}

// The backend buckets songs last.fm has no tags for under "nogenre".
export function genreLabel(name) {
  if (!name) return ''
  return name.toLowerCase() === 'nogenre' ? 'No genre' : name
}

const PALETTE = [
  'from-[#C83D4A] to-[#9E2D3A]',
  'from-[#D94B57] to-[#A66A73]',
  'from-[#A66A73] to-[#E08A92]',
  'from-[#4D8DCC] to-[#26415C]',
  'from-[#35B779] to-[#1C6B49]',
  'from-[#E5A93D] to-[#8F641F]',
  'from-[#3F4452] to-[#77737B]',
  'from-[#E05260] to-[#7A2530]',
]

export function avatarGradient(user) {
  const key = String(user?.id ?? user?.first_name ?? '?')
  let hash = 0
  for (const ch of key) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return PALETTE[hash % PALETTE.length]
}

export function formatDuration(seconds) {
  if (!seconds) return null
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function formatCount(n) {
  if (!n || n < 1) return null
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1).replace(/\.0$/, '')}M`
  if (n >= 1e3) return `${(n / 1e3).toFixed(n >= 1e4 ? 0 : 1).replace(/\.0$/, '')}k`
  return String(n)
}

export function timeAgo(dateStr) {
  const diff = (Date.now() - new Date(dateStr + 'Z').getTime()) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)}d ago`
  return new Date(dateStr + 'Z').toLocaleDateString()
}
