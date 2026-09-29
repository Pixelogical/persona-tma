import axios from 'axios'

const TOKEN_KEY = 'persona_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

const api = axios.create({
  // Relative base → works through the vite/preview proxy (port 3000),
  // through cloudflared and when the backend serves dist/ itself.
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 20000,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearToken()
      window.dispatchEvent(new Event('persona:unauthorized'))
    }
    return Promise.reject(error)
  }
)

export const errMessage = (e, fallback = 'Something went wrong') => {
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg
  return e?.message || fallback
}

export default api
