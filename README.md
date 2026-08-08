# Travel Planner MVP

A web application that automates travel research and produces an "oversaturated candidate report" for users and their travel companions to vote on, before producing a final travel guide.

## Stack

- **Frontend**: Next.js 14 (App Router), Tailwind CSS, shadcn/ui
- **Backend**: FastAPI, SQLAlchemy, Celery, PostgreSQL, Redis
- **LLM**: 硅基流动 OpenAI-compatible API
- **Deployment**: Docker Compose + Nginx reverse proxy on an existing server

## Quick Start (local)

1. Copy environment variables:
   ```bash
   cp .env.example .env
   # edit .env with your keys
   ```

2. Build and start all services:
   ```bash
   docker compose up --build
   ```

3. Open the app:
   - Frontend: http://localhost:3000
   - Backend API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/healthz

## Project Structure

```
.
├── frontend/          # Next.js application
├── backend/           # FastAPI application (app/, alembic/, tests/)
├── docs/              # API key sourcing guide, planning docs
├── openspec/          # Spec-driven change management (specs/ + changes/)
├── nginx/             # Server block for travel.umafans.run
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

## Development Notes

- The backend uses Celery workers for asynchronous data collection and report generation.
- PostgreSQL and Redis run in dedicated Docker Compose services.
- Database schema is managed by Alembic; the backend container runs
  `alembic upgrade head` automatically before uvicorn starts.
- Backend checks (run inside the container):
  ```bash
  docker compose exec backend ruff check app tests
  docker compose exec backend python -m pytest
  ```
- Frontend type check:
  ```bash
  docker compose exec frontend npx tsc --noEmit
  ```
- Sharing model: report pages require the current `/p/{share-token}` link.
  Creator authority is a 180-day, project-path-scoped HttpOnly/Secure cookie;
  the one-time recovery key must be saved offline. Anonymous voting uses a
  separate project-scoped HttpOnly cookie. No credential is placed in URLs or
  JavaScript storage.
- Browser writes require an exact configured `Origin`. Configure
  `TRUSTED_PROXY_CIDRS` before trusting forwarded client addresses and keep
  `RATE_LIMIT_REDIS_URL` available; abuse-sensitive writes fail closed.
- External API keys are optional and degrade gracefully per collector; see
  `docs/API_KEYS.md` for where to get each key and current pricing.
- Production deployment (Nginx + subdomain coexistence): see `DEPLOYMENT.md`.
