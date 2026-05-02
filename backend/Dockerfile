# Production image for FastAPI (e.g. Render "Docker" Web Service).
# Build context must be this `backend/` directory (see README).

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

# Render provides PORT; default for local docker run: -p 8000:8000
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn search_agent.main:app --host 0.0.0.0 --port \"${PORT}\""]
