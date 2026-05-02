# Seeker

LangGraph **search agent** with DuckDuckGo and Wikipedia retrieval, optional charts, optional PDF reports, Postgres (Neon) checkpoints, and a React + Vite + Tailwind UI.

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

## GitHub

This repository is intended to be published as **`seeker`**. Do not commit `.env` files; use `.env.example` only.

## License

Add your license (e.g. MIT) when you publish.
