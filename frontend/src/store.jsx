import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import api, { clearToken, getToken, setToken } from './lib/api'
import { isTMA, initTelegram, tgInitData } from './lib/telegram'

const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

let toastId = 0

export function AppProvider({ children }) {
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [me, setMe] = useState(null)
  const [toasts, setToasts] = useState([])
  const [rev, setRev] = useState(0) // bump to refresh dependent views
  const [profileUserId, setProfileUserId] = useState(null) // open profile modal
  const bootRef = useRef(false)
  const bootstrapRef = useRef(null)

  const toast = useCallback((msg, type = 'info') => {
    const id = ++toastId
    setToasts((t) => [...t, { id, msg, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3400)
  }, [])

  const refreshMe = useCallback(async () => {
    try {
      const { data } = await api.get('/me')
      setMe(data)
      return data
    } catch {
      /* handled by interceptor */
    }
  }, [])

  const applySession = useCallback((session) => {
    setToken(session.token)
    setMe(session.user)
    setStatus('ready')
  }, [])

  const loginWithTelegram = useCallback(async () => {
    const { data } = await api.post('/auth/telegram', {
      init_data: tgInitData(),
    })
    applySession(data)
  }, [applySession])

  const bootstrap = useCallback(async () => {
    // 1) INSIDE the Mini App: always, silently and permanently signed in as
    //    the Telegram account that opened it. There is no login screen and
    //    no way to switch or sign out — this is the only way in.
    if (isTMA()) {
      try {
        await loginWithTelegram()
        return
      } catch {
        clearToken()
        setStatus('error')
        return
      }
    }

    // 1b) The Telegram object exists but its init data hasn't arrived yet
    //     (Desktop injects it slightly after start) — wait and retry once.
    if (typeof window !== 'undefined' && window.Telegram?.WebApp && !getToken()) {
      setTimeout(() => {
        if (isTMA()) {
          loginWithTelegram().catch(() => {
            clearToken()
            setStatus('error')
          })
        }
      }, 1200)
    }

    // 2) OUTSIDE Telegram (plain browser link): reuse a still-valid stored
    //    session (a year long) so returning visitors stay signed in too.
    const token = getToken()
    if (token) {
      try {
        const { data } = await api.get('/me')
        setMe(data)
        setStatus('ready')
        return
      } catch {
        clearToken()
      }
    }

    // 3) No session and not inside Telegram → nothing to log into manually.
    setStatus('error')
  }, [loginWithTelegram])

  bootstrapRef.current = bootstrap

  useEffect(() => {
    // SDK/theme setup — and re-bootstrap when Telegram data shows up late
    // (ttminit / late desktop injection / URL), so a slow SDK never means
    // "sign-in failed".
    initTelegram(() => {
      bootstrapRef.current?.()
    })
  }, [])

  useEffect(() => {
    if (bootRef.current) return
    bootRef.current = true
    bootstrap()
  }, [bootstrap])

  useEffect(() => {
    // a lost/expired session silently re-signs in (Telegram only) —
    // the user never sees a login screen.
    const onUnauthorized = () => {
      setMe(null)
      bootstrap()
    }
    window.addEventListener('persona:unauthorized', onUnauthorized)
    return () => window.removeEventListener('persona:unauthorized', onUnauthorized)
  }, [bootstrap])

  const value = useMemo(
    () => ({
      status,
      me,
      toasts,
      toast,
      rev,
      profileUserId,
      openProfile: (id) => setProfileUserId(id),
      closeProfile: () => setProfileUserId(null),
      refreshAll: () => setRev((r) => r + 1),
      refreshMe,
      loginWithTelegram,
      bootstrap,
    }),
    [
      status,
      me,
      toasts,
      toast,
      rev,
      profileUserId,
      refreshMe,
      loginWithTelegram,
      bootstrap,
    ]
  )

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}
