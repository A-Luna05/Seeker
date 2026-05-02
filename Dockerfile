# Monorepo root: build context is the repo root (Render default).
# Keeps `backend/Dockerfile` usable for `docker build ./backend`.

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/src ./src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn search_agent.main:app --host 0.0.0.0 --port \"${PORT}\""]
