# Search agent backend

FastAPI + LangGraph agent with DuckDuckGo, Wikipedia, optional charts, Neon (Postgres) checkpoints, and optional PDF demo reports.

Use **[uv](https://docs.astral.sh/uv/)** to create the virtual environment and **`uv pip`** (uv’s pip-compatible installer) to install into `.venv`. Install uv once: `pip install uv` or see the uv docs for your platform.

## Setup

From the `backend` directory:

**Windows (PowerShell)**

```powershell
cd backend
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

**macOS / Linux**

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

You can run installs without activating the venv by passing the interpreter explicitly, for example:

```bash
uv pip install --python .venv/Scripts/python.exe -e ".[dev]"
# or: uv pip install --python .venv/bin/python -e ".[dev]"
```

Copy `.env.example` to `.env` and set `DATABASE_URL` (Neon connection string), `OPENAI_API_KEY`, and optionally `LITELLM_DEFAULT_MODEL`.

First run with Postgres: checkpoint tables are created in app lifespan via `AsyncPostgresSaver.setup()`.

## Run

From the `backend` folder with the venv activated and the package installed (`uv pip install -e ".[dev]"`):

**Option A — module entry (simplest)**

```bash
python -m search_agent
```

This starts Uvicorn with reload on `http://127.0.0.1:8000`. Swagger UI: `http://127.0.0.1:8000/docs`.

**Option B — explicit Uvicorn**

```bash
uvicorn search_agent.main:app --reload --app-dir src
```

Or without activating, using uv’s environment:

```bash
uv run --directory . uvicorn search_agent.main:app --reload --app-dir src
```

(`uv run` uses `.venv` when present.)

Windows alternative with `PYTHONPATH`:

```powershell
$env:PYTHONPATH = "src"
uv run uvicorn search_agent.main:app --reload
```

## Frontend (full stack)

In another terminal, from the repo’s `frontend` folder:

```bash
pnpm dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. Start the backend first, then open the URL Vite prints (often `http://localhost:5173`).

## Deploy on Render (Docker)

**Option A — repo root (simplest):** leave **Root Directory** empty. The repo has a root `Dockerfile` that copies `backend/`. Set **Dockerfile Path** to `Dockerfile` (default).

**Option B — backend only:** set **Root Directory** to `backend` and **Dockerfile Path** to `Dockerfile` (not `backend/Dockerfile`, or the path is wrong).

Steps:

1. **New → Web Service**, connect the repo, choose **Docker**.
2. Configure root directory / Dockerfile as above.
3. Add environment variables from `.env.example` (at minimum `OPENAI_API_KEY`; `DATABASE_URL` for Neon checkpoints or leave empty for in-memory).
4. Render injects **`PORT`**; the container listens on `0.0.0.0` using that port.

**Local smoke test** (from repo root):

```bash
docker build -t seeker-api ./backend
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-test -e DATABASE_URL= seeker-api
```

Or build like Render (repo root):

```bash
docker build -t seeker-api .
docker run --rm -p 8000:8000 -e OPENAI_API_KEY=sk-test -e DATABASE_URL= seeker-api
```

Then open `http://127.0.0.1:8000/docs` (use a real key for live LLM calls).

## Tests

Activate the venv (or use `uv run`) and set `PYTHONPATH` as needed:

```powershell
.venv\Scripts\activate
$env:PYTHONPATH = "src"
pytest
```
