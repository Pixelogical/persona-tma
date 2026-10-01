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
import { isTMA, tgInitData } from './lib/telegram'

const AppCtx = createContext(null)
export const useApp = () => useContext(AppCtx)

let toastId = 0

export function AppProvider({ children }) {
  const [status, setStatus] = useState('loading') // loading | login | ready | error
  const [me, setMe] = useState(null)
  const [devUsers, setDevUsers] = useState([])
  const [allowDev, setAllowDev] = useState(false)
  const [toasts, setToasts] = useState([])
  const [rev, setRev] = useState(0) // bump to refresh dependent views
  const bootRef = useRef(false)

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

  const loginAs = useCallback(
    async (payload) => {
      const { data } = await api.post('/auth/dev-login', payload)
      applySession(data)
      return data.user
    },
    [applySession]
  )

  const logout = useCallback(() => {
    clearToken()
    setMe(null)
    setStatus('login')
  }, [])

  const bootstrap = useCallback(async () => {
    // 1) INSIDE the Mini App: always sign in as the Telegram account that
    //    opened it. Never reuse a stored token, never show the dev picker.
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

    // 2) OUTSIDE Telegram (plain browser): reuse a stored session if valid.
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

    // 3) OUTSIDE Telegram only: browser dev login (backend must allow it).
    try {
      const { data } = await api.get('/auth/config')
      setAllowDev(data.allow_dev_login)
      if (data.allow_dev_login) {
        try {
          const users = await api.get('/auth/dev-users')
          setDevUsers(users.data)
        } catch {
          setDevUsers([])
        }
        setStatus('login')
      } else {
        setStatus('error')
      }
    } catch {
      setStatus('error')
    }
  }, [loginWithTelegram])

  useEffect(() => {
    if (bootRef.current) return
    bootRef.current = true
    bootstrap()
  }, [bootstrap])

  useEffect(() => {
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
      devUsers,
      allowDev,
      rev,
      refreshAll: () => setRev((r) => r + 1),
      refreshMe,
      loginAs,
      loginWithTelegram,
      bootstrap,
      logout,
    }),
    [
      status,
      me,
      toasts,
      toast,
      devUsers,
      allowDev,
      rev,
      refreshMe,
      loginAs,
      loginWithTelegram,
      bootstrap,
      logout,
    ]
  )

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>
}
