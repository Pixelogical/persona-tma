# 🎧 Persona — Telegram Mini App Music Chart

A Telegram Mini App (TMA) for the **Persona** group, powered by **PersonaBot**.

* Drop an **MP3** in the group → the bot grabs its metadata and puts it on the chart
* Vote with **5 stars** — each vote earns the voter **1 point**
* Chart tabs: **🔥 Trending · ✨ New · 🏆 Top**
* **Playlists** — everyone's lists are public, press **Play** and the bot streams
  every track (in order) into the group chat through itself
* **Podium** of the top-3 voters; they can **📌 pin** a song for everyone —
  clicking a pinned card deep-links to that song's message in Telegram
* User profiles = circle avatar with the person's initials
* UI: React + Vite + Tailwind + **daisyUI** (dark, glassmorphism, mobile-first)
* API: FastAPI + **aiogram 3** + SQLAlchemy + **SQLite** (WAL)

```
persona/
├── backend/            FastAPI + aiogram
│   ├── .env.example    ← copy to .env and edit (token, proxy, …)
│   ├── config.py       every setting in one place
│   ├── main.py         app entry (also serves frontend/dist if built)
│   ├── models.py       User / Song / Vote / Playlist / PlaylistSong / Pin
│   ├── bot/            aiogram handlers + playlist playback engine
│   └── api/            REST endpoints (auth, songs, playlists, pins, users)
└── frontend/           React (vite) + daisyUI — runs on :3000
```

## Ports

| Service  | Port | Notes                                        |
|----------|------|----------------------------------------------|
| Frontend | 3000 | point **cloudflared** here                    |
| Backend  | 8080 | `/api` — proxied by vite, not publicly needed |

The frontend always calls the **relative** path `/api`, so one single tunnel on
port 3000 serves everything, both in the browser and inside Telegram.

## 1 · Install (on the server)

Backend (venv created by you, config lives entirely in `backend/.env`):

```bash
cd backend
cp .env.example .env        # then edit it
python3 -m venv venv
venv/bin/pip install -U pip
venv/bin/pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

Required in `backend/.env`:

* `BOT_TOKEN` — from @BotFather
* `WEBAPP_URL` — `https://t.me/PersonaBot/<app>` after creating the Mini App
* `USE_PROXY=true` + `PROXY_URL=http://user:pass@host:port` (or `socks5://…`) to
  reach Telegram through an HTTP/SOCKS proxy
* optional `PERSONA_CHAT_ID=-100…` to only ingest songs from the Persona group
* `ALLOW_DEV_LOGIN=true` lets you open the URL in a **normal browser** and pick
  a test user (turn it off in production — inside Telegram real TMA auth with
  HMAC verification of `initData` is always used)

> ⚠️ For pinned-song deep links (`https://t.me/<group>/<message_id>`) to work,
> the group must be **public** (have a @username). For private groups the bot
> falls back to `tg://` chat links or `CHAT_LINK_TEMPLATE`.

## 2 · Run

Two terminals (backend :8080, frontend :3000):

```bash
# terminal 1 — backend
cd backend && venv/bin/python main.py

# terminal 2 — frontend
cd frontend
npm run build        # first run (and after frontend changes)
npm run preview      # production preview on :3000
# or, during development (hot reload on :3000):
npm run dev
```

Or as one background command with nohup:

```bash
(cd backend && nohup venv/bin/python main.py >/tmp/persona-api.log 2>&1 &)
cd frontend && nohup npm run preview >/tmp/persona-ui.log 2>&1 &
```

Tunnel (already your workflow):

```bash
cloudflared tunnel --url http://localhost:3000
```

> The backend also serves `frontend/dist` directly on :8080 if it exists, so you
> can alternatively tunnel straight to :8080 with zero node processes running.

## 3 · Telegram configuration

1. @BotFather → `/newapp` (or Bot Settings → Menu Button) → choose the Persona
   group → paste your tunnel URL. Suggested: set the **Menu Button** to the app
   URL so the group gets a "🎧 Open Chart" button.
2. Add **PersonaBot** to the **Persona** group.
3. Bot must be allowed to **send messages** (don't leave it as a silent admin).

## 4 · API overview

```
POST /api/auth/telegram        verify WebApp initData → session token
POST /api/auth/dev-login       browser testing (when ALLOW_DEV_LOGIN)
GET  /api/me                   profile, points, rank, is_top3
GET  /api/users/top            podium (top 3 voters)
GET  /api/songs?tab=trending   chart (trending | new | top)
POST /api/songs/{id}/vote      {"value": 1..5} → +1 point
GET  /api/pins                 pinned cards (public)
POST /api/pins                 {"song_id"} (top-3 only) — replaces your pin
GET  /api/playlists            public playlists
POST /api/playlists            create
POST /api/playlists/{id}/songs / DELETE .../songs/{song_id}
POST /api/playlists/{id}/play  bot forwards every track to the group, in order
```

## Rating logic

* **Top** = Bayesian average (shrinks songs with few votes toward the global mean)
* **Trending** = star-weighted votes with exponential time decay + fresh-track boost
* **New** = newest first

Every saved vote gives the voter **1 point** — points drive the podium and the
top-3 "pin power".
