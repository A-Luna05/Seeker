# Seeker

LangGraph **search Agent** with DuckDuckGo and Wikipedia retrieval, optional charts, optional PDF reports, Postgres (Neon) checkpoints, and a React + Vite + Tailwind UI.

## Repository layout

| Path        | Description |
|------------|-------------|
| `backend/` | FastAPI app (`search_agent` package), LiteLLM, graph nodes, `/api` routes |
| `frontend/`| Vite + React + TypeScript client (proxies `/api` to the backend) |

## Quick start

### Backend

From `backend/`:

```powershell
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
copy .env.example .env
# Edit .env: OPENAI_API_KEY, optional DATABASE_URL, LITELLM_DEFAULT_MODEL
python -m search_agent
```

API: `http://127.0.0.1:8000` — docs at `/docs`.

### Frontend

From `frontend/`:

```powershell
pnpm install
pnpm dev
```

Set `VITE_API_URL` if the API is not the default Vite proxy target (see `frontend/.env.example`).

## Deploy frontend on Netlify

Your API calls use **`VITE_API_URL`** at **build time** (Vite inlines it). Locally, leaving it unset uses relative `/api` URLs and the Vite dev proxy.

### 1. Host the backend somewhere public first

Examples: [Railway](https://railway.app), [Render](https://render.com), [Fly.io](https://fly.io), [Google Cloud Run](https://cloud.google.com/run), or any VM with HTTPS. The FastAPI app must expose something like `https://your-api.example.com` with the same routes under `/api/...`.

Your `main.py` already sets `CORSMiddleware` with `allow_origins=["*"]`, so the browser can call the API directly.

### 2. Netlify site settings

- **Connect** the Git repo and pick the branch (e.g. `main`).
- Netlify reads **`netlify.toml`** at the repo root: build runs inside **`frontend/`**, output is **`dist/`**.

### 3. Environment variable (recommended)

In Netlify: **Site configuration → Environment variables → Build** (and optionally **Deploy** if you use runtime features; for Vite, **build** is what matters).

| Name            | Example value |
|-----------------|---------------|
| `VITE_API_URL`  | `https://your-api.example.com` (no trailing slash) |

Redeploy after changing variables so the client bundle is rebuilt.

### 4. Same-origin `/api` instead (optional)

If you **do not** set `VITE_API_URL`, the built app requests `/api/...` on the Netlify domain. Then add a **rewrite proxy** in `netlify.toml`: uncomment the `/api/*` redirect block and set `to = "https://your-api.example.com/api/:splat"`. Redeploy.

### 5. `pnpm` on Netlify

The repo’s `frontend/pnpm-lock.yaml` is enough for Netlify to use pnpm. `NODE_VERSION` is set in `netlify.toml`.

## GitHub

This repository is intended to be published as **`seeker`**. Do not commit `.env` files; use `.env.example` only.

## License

Add your license (e.g. MIT) when you publish.
