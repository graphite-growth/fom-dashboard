# Project Context

## Do not modify

Hidden folders (`.elasticbeanstalk`, `.github`, `.platform`), `docker-compose.yml`, `scripts/`, `proxy/`.

## Architecture

- `backend/` — FastAPI (Python 3.13+, uv). See `backend/CLAUDE.md`.
- `frontend/` — Next.js (TypeScript, Bun). See `frontend/CLAUDE.md`.
- `proxy/` — Nginx: `/api/v1/*` → backend (prefix stripped), everything else → frontend.

Read the corresponding `CLAUDE.md` before working in `frontend/` or `backend/`.

## Local development (preferred)

`DEV_AUTH=true` bypasses Google OAuth with a fake user (`dev@example.com`).

**Backend** (terminal 1):
```bash
cd backend && uv sync
AUTH_SECRET=dev-secret-key AUTH_URL=http://localhost:3000 ALLOWED_DOMAIN=example.com DEV_AUTH=true \
  uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend** (terminal 2):
```bash
cd frontend && bun install
BACKEND_URL=http://localhost:8000 bun dev   # http://localhost:3000
```

Next.js rewrites `/api/v1/*` to the backend, stripping the prefix (matching nginx).

## E2E tests (Docker)

Full Docker for E2E or production-like validation only:
```bash
docker compose build && docker compose up -d   # http://localhost
```

## Rules

1. Do not use `2>&1` redirection in bash commands.
