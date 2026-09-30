import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const proxy = {
  '/api': {
    target: process.env.VITE_BACKEND || 'http://127.0.0.1:8080',
    changeOrigin: true,
  },
}

// The app is served on :3000 (behind cloudflared) and talks to the
// FastAPI backend on :8080 through the /api proxy below — one single
// public URL is enough for both browser and Telegram Mini App.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    strictPort: true,
    proxy,
    allowedHosts: ['.trycloudflare.com'], // Or set `allowedHosts: true` to allow all hosts
  },
  preview: {
    port: 3000,
    host: true,
    strictPort: true,
    proxy,
    allowedHosts: ['.trycloudflare.com'],
  },
})
